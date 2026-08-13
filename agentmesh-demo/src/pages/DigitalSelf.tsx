import { WelcomeHero } from '../components/digital-self/WelcomeHero'
import { IdentityCard } from '../components/digital-self/IdentityCard'
import { UnderstandingList } from '../components/digital-self/UnderstandingList'
import { TodayWork } from '../components/digital-self/TodayWork'
import { RecentGrowth } from '../components/digital-self/RecentGrowth'
import { MyImpact } from '../components/digital-self/MyImpact'

export function DigitalSelf() {
  return (
    <div className="space-y-6">
      <WelcomeHero />
      <IdentityCard />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <UnderstandingList />
        <TodayWork />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentGrowth />
        <MyImpact />
      </div>
    </div>
  )
}
