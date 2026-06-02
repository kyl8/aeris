"""Download Sentinel-2 true-color imagery for Aeris historical evaluation.

This script searches the Copernicus Data Space Ecosystem (CDSE) STAC API and
downloads True Color assets for the Baixada Santista study area. The output
directory is the same one consumed by ``api/climate_pipeline.py``.

Expected .env variables:
    CDSE_USERNAME=<your Copernicus Data Space username>
    CDSE_PASSWORD=<your Copernicus Data Space password>
    CDSE_TOTP=<optional 2FA code, only when required by your account>
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from PIL import Image
import requests
from dotenv import load_dotenv
from pystac import Asset, Item
from pystac_client import Client

from aeris.logging import configure_logging as configure_aeris_logging


LOGGER = logging.getLogger("download_satellite_dataset")
Image.MAX_IMAGE_PIXELS = None

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_OUTPUT_DIR = CURRENT_DIR / "datasets" / "historical_eval"

CDSE_STAC_ENDPOINT = "https://stac.dataspace.copernicus.eu/v1/"
CDSE_TOKEN_ENDPOINT = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
    "protocol/openid-connect/token"
)

STAC_COLLECTION = "sentinel-2-l2a"
PRODUCT_TYPE = "S2MSI2A"
BAIXADA_SANTISTA_BBOX = [-46.45, -24.05, -46.25, -23.90]
DEFAULT_TIME_RANGE = "2015-01-01T00:00:00Z/2026-05-17T23:59:59Z"
DEFAULT_FILENAME_TIMEZONE = "America/Sao_Paulo"

TRUE_COLOR_ASSET_PRIORITY = (
    "thumbnail",
    "visual",
    "TCI",
    "tci",
    "true_color",
    "true-color",
    "overview",
)
CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class CDSECredentials:
    username: str
    password: str
    totp: str | None = None


@dataclass(slots=True)
class CDSETokenProvider:
    """Small OAuth2 token provider with explicit refresh support."""

    credentials: CDSECredentials
    timeout_seconds: float
    access_token: str | None = None

    def get_token(self) -> str:
        if self.access_token is None:
            self.refresh()
        if self.access_token is None:
            raise RuntimeError("CDSE access token nao foi obtido.")
        return self.access_token

    def refresh(self) -> str:
        payload = {
            "client_id": "cdse-public",
            "username": self.credentials.username,
            "password": self.credentials.password,
            "grant_type": "password",
        }
        if self.credentials.totp:
            payload["totp"] = self.credentials.totp

        LOGGER.info("Obtendo access token CDSE via OAuth2.")
        response = requests.post(
            CDSE_TOKEN_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        token_payload = response.json()
        token = token_payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Resposta de autenticacao CDSE nao contem access_token.")

        self.access_token = token
        return token


@dataclass(frozen=True, slots=True)
class DownloadCandidate:
    item: Item
    asset_key: str
    asset: Asset
    timestamp_utc: datetime
    output_path: Path


@dataclass(frozen=True, slots=True)
class DownloadRunOptions:
    output_dir: Path = DEFAULT_OUTPUT_DIR
    env_file: Path = DEFAULT_ENV_FILE
    datetime_range: str = DEFAULT_TIME_RANGE
    max_items: int | None = None
    filename_timezone: str = DEFAULT_FILENAME_TIMEZONE
    request_timeout: float = 60.0
    sleep_seconds: float = 1.5
    overwrite: bool = False
    dry_run: bool = False
    progress_callback: Callable[[str], None] | None = None


@dataclass(frozen=True, slots=True)
class DownloadRunSummary:
    total_items: int
    candidates: int
    downloaded: int
    skipped_existing: int
    failed: int
    dry_run: bool
    output_dir: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pesquisa e descarrega imagens Sentinel-2 L2A True Color do CDSE "
            "para o dataset historico do Aeris."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Diretorio de saida das imagens .jpg. Padrao: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"Arquivo .env com CDSE_USERNAME/CDSE_PASSWORD. Padrao: {DEFAULT_ENV_FILE}",
    )
    parser.add_argument(
        "--datetime",
        default=DEFAULT_TIME_RANGE,
        help=f"Intervalo temporal STAC. Padrao: {DEFAULT_TIME_RANGE}",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Limite opcional de items STAC para testes. Por padrao processa todos.",
    )
    parser.add_argument(
        "--filename-timezone",
        default=DEFAULT_FILENAME_TIMEZONE,
        help=(
            "Timezone usada no nome do arquivo. Use UTC se quiser nomes em UTC. "
            f"Padrao: {DEFAULT_FILENAME_TIMEZONE}"
        ),
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=60.0,
        help="Timeout em segundos para autenticacao e downloads.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.5,
        help="Pausa entre downloads para reduzir risco de rate-limit.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve arquivos ja existentes. Por padrao, arquivos existentes sao pulados.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa pesquisa e planejamento sem baixar arquivos.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    configure_aeris_logging("INFO")


def load_cdse_credentials(env_file: Path) -> CDSECredentials:
    load_dotenv(env_file)
    username = os.getenv("CDSE_USERNAME")
    password = os.getenv("CDSE_PASSWORD")
    totp = os.getenv("CDSE_TOTP") or None

    if not username or not password:
        raise RuntimeError(
            f"Credenciais CDSE ausentes. Defina CDSE_USERNAME e CDSE_PASSWORD em {env_file}.",
        )

    return CDSECredentials(username=username, password=password, totp=totp)


def iter_stac_items(datetime_range: str, max_items: int | None) -> list[Item]:
    LOGGER.info("Abrindo STAC CDSE: %s", CDSE_STAC_ENDPOINT)
    catalog = Client.open(CDSE_STAC_ENDPOINT)
    
    # CDSE permite máximo 200 items para Sentinel-2 L2A.
    # Usamos 100 por página para iterar através de múltiplas páginas
    search = catalog.search(
        collections=[STAC_COLLECTION],
        bbox=BAIXADA_SANTISTA_BBOX,
        datetime=datetime_range,
        limit=100,
    )

    items: list[Item] = []
    count = 0
    page_count = 0
    max_retries = 3
    
    LOGGER.info("Iniciando iteracao por todas as paginas STAC...")
    
    for item in search.items():
        try:
            items.append(item)
            count += 1
            
            if max_items is not None and count >= max_items:
                LOGGER.info("Atingido limite de %d items. Parando iteracao.", max_items)
                break
            
            # Log a cada 100 items para acompanhar progresso
            if count % 100 == 0:
                LOGGER.info("Carregados %d items do STAC...", count)
                time.sleep(1)  # Pausa entre lotes
            
            time.sleep(0.05)  # Pequena pausa entre items
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            LOGGER.warning("Erro de conexao ao iterar STAC (item %d). Continuando com items ja carregados: %s", count, exc)
            break
        except Exception as exc:
            LOGGER.exception("Erro inesperado ao iterar STAC no item %d: %s", count, exc)
            break
    
    LOGGER.info("Total de items STAC carregados: %d (em %d lotes)", len(items), (count // 100) + 1)
    return items


def parse_item_datetime(item: Item) -> datetime:
    if item.datetime is not None:
        timestamp = item.datetime
    else:
        raw_datetime = item.properties.get("datetime")
        if not isinstance(raw_datetime, str):
            raise ValueError(f"Item {item.id} nao possui datetime valido.")
        timestamp = datetime.fromisoformat(raw_datetime.replace("Z", "+00:00"))

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def is_s2msi2a_item(item: Item) -> bool:
    """Keep only Sentinel-2 Level-2A/S2MSI2A products.

    In the current CDSE STAC, the collection itself is sentinel-2-l2a. The
    additional checks keep the script safe if metadata changes or another
    collection is passed in future refactors.
    """

    if (item.collection_id or "").lower() == STAC_COLLECTION:
        return True

    haystack = " ".join(
        str(value)
        for value in [
            item.id,
            item.properties.get("productType"),
            item.properties.get("product:type"),
            item.properties.get("s2:product_type"),
            item.properties.get("processing:level"),
            item.properties.get("title"),
        ]
        if value is not None
    ).upper()
    return PRODUCT_TYPE in haystack or "LEVEL-2A" in haystack or "L2A" in haystack


def asset_score(asset_key: str, asset: Asset) -> int:
    searchable = " ".join(
        part
        for part in [
            asset_key,
            asset.title or "",
            asset.description or "",
            asset.media_type or "",
            " ".join(asset.roles or []),
        ]
        if part
    ).lower()

    href_scheme = urlparse(asset.href or "").scheme.lower()
    is_http_asset = href_scheme in {"http", "https"}
    is_jpeg_asset_type = "jpeg" in searchable or "jpg" in searchable

    if is_http_asset and is_jpeg_asset_type and ("thumbnail" in searchable or "quicklook" in searchable):
        return 140
    if asset_key in TRUE_COLOR_ASSET_PRIORITY:
        base_score = 100 - TRUE_COLOR_ASSET_PRIORITY.index(asset_key)
        if is_http_asset:
            base_score += 20
        return base_score
    if "true color" in searchable or "true-colour" in searchable:
        return 80
    if "visual" in searchable:
        return 70
    if "tci" in searchable:
        return 60
    if "thumbnail" in searchable or "quicklook" in searchable:
        return 20
    return 0


def report_progress(callback: Callable[[str], None] | None, message: str) -> None:
    LOGGER.info(message)
    if callback is not None:
        callback(message)


def find_true_color_asset(item: Item) -> tuple[str, Asset] | None:
    scored_assets = [
        (asset_score(asset_key, asset), asset_key, asset)
        for asset_key, asset in item.assets.items()
    ]
    scored_assets.sort(key=lambda entry: entry[0], reverse=True)

    for score, asset_key, asset in scored_assets:
        if score > 0 and asset.href:
            return asset_key, asset
    return None


def format_timestamp_for_filename(timestamp_utc: datetime, timezone_name: str) -> str:
    output_timezone = ZoneInfo(timezone_name)
    localized = timestamp_utc.astimezone(output_timezone)
    return localized.strftime("%Y-%m-%d_%H-%M")


def build_candidates(items: list[Item], output_dir: Path, filename_timezone: str) -> list[DownloadCandidate]:
    candidates: list[DownloadCandidate] = []
    skipped_non_l2a = 0
    skipped_without_asset = 0

    for item in items:
        if not is_s2msi2a_item(item):
            skipped_non_l2a += 1
            continue

        asset_pair = find_true_color_asset(item)
        if asset_pair is None:
            skipped_without_asset += 1
            LOGGER.warning("Item %s sem asset True Color reconhecido. Assets: %s", item.id, list(item.assets))
            continue

        timestamp_utc = parse_item_datetime(item)
        timestamp_label = format_timestamp_for_filename(timestamp_utc, filename_timezone)
        output_path = output_dir / f"{timestamp_label}.jpg"
        asset_key, asset = asset_pair
        candidates.append(
            DownloadCandidate(
                item=item,
                asset_key=asset_key,
                asset=asset,
                timestamp_utc=timestamp_utc,
                output_path=output_path,
            ),
        )

    LOGGER.info(
        "Candidatos de download: %d | ignorados nao-L2A: %d | sem True Color: %d",
        len(candidates),
        skipped_non_l2a,
        skipped_without_asset,
    )
    return candidates


def temporary_asset_path(output_path: Path, asset_href: str) -> Path:
    asset_suffix = Path(urlparse(asset_href).path).suffix
    if not asset_suffix or len(asset_suffix) > 12:
        asset_suffix = ".bin"
    return output_path.with_suffix(output_path.suffix + asset_suffix + ".part")


def stream_download_to_temp_file(response: requests.Response, temp_path: Path) -> int:
    bytes_written = 0

    with temp_path.open("wb") as file_handle:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE_BYTES):
            if not chunk:
                continue
            file_handle.write(chunk)
            bytes_written += len(chunk)

    if bytes_written == 0:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Download vazio para {temp_path.name}.")

    return bytes_written


def is_jpeg_asset(asset_href: str, content_type: str) -> bool:
    href_suffix = Path(urlparse(asset_href).path).suffix.lower()
    return href_suffix in {".jpg", ".jpeg"} or "jpeg" in content_type.lower() or "jpg" in content_type.lower()


def finalize_as_jpeg(temp_path: Path, output_path: Path, asset_href: str, content_type: str) -> None:
    if is_jpeg_asset(asset_href, content_type):
        temp_path.replace(output_path)
        return

    LOGGER.info(
        "Convertendo asset '%s' (%s) para JPEG valido: %s",
        Path(urlparse(asset_href).path).suffix or "sem extensao",
        content_type or "Content-Type desconhecido",
        output_path.name,
    )
    try:
        with Image.open(temp_path) as image:
            image.convert("RGB").save(output_path, format="JPEG", quality=95, optimize=True)
    finally:
        temp_path.unlink(missing_ok=True)


def download_asset(
    session: requests.Session,
    token_provider: CDSETokenProvider,
    candidate: DownloadCandidate,
    timeout_seconds: float,
) -> int:
    href = candidate.asset.href
    href_scheme = urlparse(href).scheme.lower()
    if href_scheme not in {"http", "https"}:
        raise RuntimeError(
            f"Asset {candidate.asset_key} do item {candidate.item.id} usa esquema '{href_scheme}'. "
            "Use um asset HTTP/JPEG ou implemente credenciais S3 CDSE para assets JP2.",
        )
    last_response_text = ""

    for attempt in range(2):
        token = token_provider.get_token()
        response = session.get(
            href,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=timeout_seconds,
            allow_redirects=True,
        )

        if response.status_code == 401 and attempt == 0:
            LOGGER.warning("Token expirado/negado em %s. Renovando e tentando novamente.", candidate.item.id)
            token_provider.refresh()
            continue

        if not response.ok:
            try:
                last_response_text = response.text[:500]
            finally:
                response.close()
            response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        temp_path = temporary_asset_path(candidate.output_path, href)
        try:
            bytes_written = stream_download_to_temp_file(response, temp_path)
            finalize_as_jpeg(temp_path, candidate.output_path, href, content_type)
            return bytes_written
        finally:
            response.close()

    raise RuntimeError(f"Falha de download apos renovacao de token. Resposta: {last_response_text}")


def run_downloads(
    candidates: list[DownloadCandidate],
    token_provider: CDSETokenProvider | None,
    overwrite: bool,
    dry_run: bool,
    timeout_seconds: float,
    sleep_seconds: float,
    progress_callback: Callable[[str], None] | None = None,
) -> DownloadRunSummary:
    total = len(candidates)
    downloaded = 0
    skipped_existing = 0
    failed = 0

    with requests.Session() as session:
        for index, candidate in enumerate(candidates, start=1):
            output_path = candidate.output_path
            if output_path.exists() and not overwrite:
                skipped_existing += 1
                report_progress(
                    progress_callback,
                    f"Saltando {index}/{total}; ficheiro ja existe: {output_path.name}",
                )
                continue

            if dry_run:
                report_progress(
                    progress_callback,
                    f"[DRY RUN] {index}/{total} item={candidate.item.id} asset={candidate.asset_key} -> {output_path.name}",
                )
                continue

            try:
                if token_provider is None:
                    raise RuntimeError("Token provider ausente. Configure CDSE_USERNAME/CDSE_PASSWORD no .env.")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                bytes_written = download_asset(
                    session=session,
                    token_provider=token_provider,
                    candidate=candidate,
                    timeout_seconds=timeout_seconds,
                )
                downloaded += 1
                report_progress(
                    progress_callback,
                    f"Descarregado ficheiro {index} de {total}: {output_path.name} ({bytes_written / (1024 * 1024):0.2f} MB)",
                )
            except Exception:
                failed += 1
                LOGGER.exception("Falha ao descarregar item %s para %s.", candidate.item.id, output_path.name)
            finally:
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

    LOGGER.info(
        "Resumo: baixados=%d | existentes=%d | falhas=%d | candidatos=%d",
        downloaded,
        skipped_existing,
        failed,
        total,
    )
    output_dir = str(candidates[0].output_path.parent) if candidates else str(DEFAULT_OUTPUT_DIR)
    
    summary_message = (
        f"✓ Download concluido com sucesso!\n"
        f"  • Baixados: {downloaded}\n"
        f"  • Existentes (pulados): {skipped_existing}\n"
        f"  • Falhas: {failed}\n"
        f"  • Total processado: {total} candidatos\n"
        f"  • Local: {output_dir}"
    )
    report_progress(None, summary_message)
    
    return DownloadRunSummary(
        total_items=total,
        candidates=total,
        downloaded=downloaded,
        skipped_existing=skipped_existing,
        failed=failed,
        dry_run=dry_run,
        output_dir=output_dir,
    )


def run_satellite_download(options: DownloadRunOptions) -> DownloadRunSummary:
    report_progress(options.progress_callback, f"Dataset Aeris de saida: {options.output_dir}")
    LOGGER.info("BBOX Baixada Santista: %s", BAIXADA_SANTISTA_BBOX)
    LOGGER.info("Periodo STAC: %s", options.datetime_range)
    LOGGER.info("Colecao STAC: %s (%s)", STAC_COLLECTION, PRODUCT_TYPE)
    LOGGER.info("Sem filtro de cloud_cover: imagens nubladas/tempestades serao mantidas.")

    token_provider: CDSETokenProvider | None = None
    if not options.dry_run:
        credentials = load_cdse_credentials(options.env_file)
        token_provider = CDSETokenProvider(credentials=credentials, timeout_seconds=options.request_timeout)

    report_progress(options.progress_callback, "Consultando STAC CDSE...")
    items = iter_stac_items(datetime_range=options.datetime_range, max_items=options.max_items)
    
    if len(items) == 0:
        report_progress(options.progress_callback, "⚠️ Nenhum item encontrado no STAC para este periodo.")
        return DownloadRunSummary(
            total_items=0,
            candidates=0,
            downloaded=0,
            skipped_existing=0,
            failed=0,
            dry_run=options.dry_run,
            output_dir=str(options.output_dir),
        )
    
    hit_max_limit = options.max_items is not None and len(items) == options.max_items
    if hit_max_limit:
        report_progress(
            options.progress_callback, 
            f"ℹ️ Limite maximo de {options.max_items} items atingido. Pode haver mais imagens disponiveis."
        )
    elif options.max_items is None:
        report_progress(
            options.progress_callback,
            f"✓ Fetching MAXIMO de imagens disponiveis (sem limite). Encontrados: {len(items)} items."
        )
    
    report_progress(options.progress_callback, f"Iniciando avaliacao de {len(items)} candidates...")
    candidates = build_candidates(
        items=items,
        output_dir=options.output_dir,
        filename_timezone=options.filename_timezone,
    )
    summary = run_downloads(
        candidates=candidates,
        token_provider=token_provider,
        overwrite=options.overwrite,
        dry_run=options.dry_run,
        timeout_seconds=options.request_timeout,
        sleep_seconds=options.sleep_seconds,
        progress_callback=options.progress_callback,
    )
    return DownloadRunSummary(
        total_items=len(items),
        candidates=summary.candidates,
        downloaded=summary.downloaded,
        skipped_existing=summary.skipped_existing,
        failed=summary.failed,
        dry_run=summary.dry_run,
        output_dir=str(options.output_dir),
    )


def main() -> None:
    configure_logging()
    args = parse_args()

    run_satellite_download(
        DownloadRunOptions(
            output_dir=args.output_dir,
            env_file=args.env_file,
            datetime_range=args.datetime,
            max_items=args.max_items,
            filename_timezone=args.filename_timezone,
            request_timeout=args.request_timeout,
            sleep_seconds=args.sleep_seconds,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        ),
    )


if __name__ == "__main__":
    main()
