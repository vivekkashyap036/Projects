import { Printer } from 'lucide-react'
import { resume } from './data/resume'
import Header from './components/Header'
import Section from './components/Section'
import Experience from './components/Experience'
import Education from './components/Education'
import Skills from './components/Skills'
import Projects from './components/Projects'

function App() {
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex justify-end mb-4 no-print">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <Printer size={16} /> Save as PDF
          </button>
        </div>

        <main className="bg-white dark:bg-neutral-900 rounded-xl shadow-sm print-shadow-none border border-neutral-200 dark:border-neutral-800 p-6 sm:p-10">
          <Header resume={resume} />

          {resume.summary && (
            <Section title="Summary">
              <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
                {resume.summary}
              </p>
            </Section>
          )}

          <Experience items={resume.experience} />
          <Education items={resume.education} />
          <Skills items={resume.skills} />
          <Projects items={resume.projects} />
        </main>
      </div>
    </div>
  )
}

export default App
