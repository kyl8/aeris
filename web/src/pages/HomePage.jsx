import {
  apiReference,
  docsLinks,
  headerNavItems,
  sidebarItems,
} from '../data/landingContent'
import { useHealth } from '../hooks/useHealth'
import { DocsHeader } from '../components/layout/DocsHeader'
import { DocsSidebar } from '../components/layout/DocsSidebar'
import { CapabilitySection } from '../components/sections/CapabilitySection'
import { EndpointSection } from '../components/sections/EndpointSection'
import { HeroSection } from '../components/sections/HeroSection'
import { PageShell } from '../components/layout/PageShell'
import { PredictionSection } from '../components/sections/PredictionSection'

export function HomePage() {
  const { health, isLoading } = useHealth()

  return (
    <PageShell>
      <DocsHeader links={docsLinks} navItems={headerNavItems} />

      <div className="mx-auto grid w-full max-w-7xl lg:grid-cols-[280px_minmax(0,1fr)]">
        <DocsSidebar items={sidebarItems} health={health} isLoading={isLoading} />

        <main className="min-w-0 px-4 py-8 sm:px-6 lg:px-10">
          <div className="max-w-4xl space-y-12">
            <HeroSection
              health={health}
              isHealthLoading={isLoading}
              docsUrl={docsLinks.swagger}
              redocUrl={docsLinks.redoc}
            />

            <CapabilitySection />

            <EndpointSection endpoints={apiReference} />

            <PredictionSection />
          </div>
        </main>
      </div>
    </PageShell>
  )
}