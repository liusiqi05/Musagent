const PageHeader = ({ badge, title, description, children }) => (

  <div className="page-header text-center mb-10 md:mb-14">

    {badge && <p className="badge inline-block mb-4 md:mb-5 px-4 py-1.5 rounded-full text-xs tracking-widest">{badge}</p>}

    <h1 className="text-3xl md:text-4xl lg:text-5xl font-cjk font-semibold leading-snug tracking-wide">{title}</h1>

    {description && (

      <p className="page-header-desc mt-4 md:mt-5 text-[15px] md:text-base max-w-2xl mx-auto leading-[1.85] font-cjk">

        {description}

      </p>

    )}

    {children}

  </div>

);



export default PageHeader;

