import { resume } from './data/resume'
import Header from './components/Header'
import Experience from './components/Experience'
import Education from './components/Education'
import Skills from './components/Skills'
import { Languages, Extracurricular } from './components/Extras'

function App() {
  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-950 py-10 px-4">
      <div className="max-w-4xl mx-auto">
        <main className="bg-white dark:bg-neutral-900 rounded-2xl shadow-xl print-shadow-none border border-neutral-200 dark:border-neutral-800 overflow-hidden">
          <Header resume={resume} />

          <div className="grid md:grid-cols-[260px_1fr] gap-x-10 gap-y-8 p-6 sm:p-10">
            <aside className="space-y-8 md:order-1 md:border-r md:border-neutral-100 md:dark:border-neutral-800 md:pr-8">
              <Skills groups={resume.skills} />
              <Education items={resume.education} />
              <Languages items={resume.languages} />
              <Extracurricular items={resume.extracurricular} />
            </aside>

            <div className="md:order-2">
              <Experience items={resume.experience} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
