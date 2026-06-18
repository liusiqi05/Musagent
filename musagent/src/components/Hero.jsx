import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { SplitText } from "gsap/all";
import { useRef } from "react";
import { Link } from "react-router-dom";

const Hero = () => {
 const videoRef = useRef();
 
 useGSAP(() => {
	const heroSplit = new SplitText(".title", {
	 type: "chars, words",
	});
	
	// Apply text-gradient class once before animating
	heroSplit.chars.forEach((char) => char.classList.add("text-gradient"));
	
	gsap.from(heroSplit.chars, {
	 yPercent: 100,
	 duration: 1.8,
	 ease: "expo.out",
	 stagger: 0.06,
	});
	
	gsap.from(".hero-desc", {
	 opacity: 0,
	 yPercent: 100,
	 duration: 1.8,
	 ease: "expo.out",
	 delay: 0.8,
	});
	
	gsap.from(".hero-yellow-tag", {
	 opacity: 0,
	 x: 40,
	 duration: 1.2,
	 ease: "power2.out",
	 delay: 1.2,
	});
	
	gsap
	.timeline({
	 scrollTrigger: {
		trigger: "#hero",
		start: "top top",
		end: "bottom top",
		scrub: true,
	 },
	})
	.to(".right-leaf", { y: 200 }, 0)
	.to(".left-leaf", { y: -200 }, 0)
	.to(".arrow", { y: 100 }, 0);
 }, []);
 
 return (
	<>
	 <section id="hero" className="noisy relative overflow-hidden flex items-center justify-center">
		{/* 背景视频 — 融入而非割裂 */}
		<video
		 ref={videoRef}
		 muted
		 loop
		 playsInline
		 autoPlay
		 src="/videos/output.mp4"
		 className="absolute inset-0 w-full h-full object-cover opacity-30"
		/>
		
		{/* 居中：MUSAGENT 标题 + 副描述 */}
		<div className="relative z-10 text-center px-5">
			<h1 className="title">MUSAGENT</h1>
			<p className="hero-desc mt-4 md:mt-6 text-sm md:text-base lg:text-lg max-w-2xl mx-auto leading-relaxed font-cjk"
			   style={{ color: 'var(--text-secondary)' }}>
				输入主题，检索参考，生成属于你的诗词与散文。
				面向创作者，而非演示面板。
			</p>
			<Link to="/inspire" className="hero-desc inline-block mt-6 px-6 py-2.5 rounded-full border border-white/15 hover:border-yellow hover:text-yellow transition-colors text-sm">
				开始创作
			</Link>
		</div>
		
		{/* 右下角：黄色标语 */}
		<p className="hero-yellow-tag absolute bottom-8 md:bottom-12 right-5 md:right-10 z-10 text-right font-cjk text-lg md:text-2xl lg:text-3xl text-yellow max-w-sm md:max-w-md leading-relaxed">
			连接诗词与艺术<br className="md:hidden" />的文学灵感平台
		</p>
		
		<img
		 src="/images/hero-left-leaf.png"
		 alt="left-leaf"
		 className="left-leaf"
		/>
		<img
		 src="/images/hero-right-leaf.png"
		 alt="right-leaf"
		 className="right-leaf"
		/>
	 </section>
	</>
 );
};

export default Hero;
