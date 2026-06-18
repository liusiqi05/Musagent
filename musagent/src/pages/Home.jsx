import Hero from '../components/Hero.jsx'
import CreatorSteps from '../components/CreatorSteps.jsx'
import MusAgentVsLLM from '../components/MusAgentVsLLM.jsx'
import Contact from '../components/Contact.jsx'

const Home = () => {
  return (
    <>
      <Hero />
      <section className="page-manuscript py-14 md:py-16">
        <div className="container mx-auto px-5 max-w-5xl">
          <MusAgentVsLLM />
        </div>
      </section>
      <CreatorSteps />
      <Contact />
    </>
  )
}

export default Home
