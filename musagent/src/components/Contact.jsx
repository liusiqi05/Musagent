import { Link } from 'react-router-dom';
import { ROUTES } from '../config/routes.js';

const Contact = () => (
  <footer id="contact" className="py-16 px-5 border-t" style={{ borderColor: 'var(--border-color)' }}>
    <div className="container mx-auto max-w-4xl text-center">
      <h2 className="font-cjk text-2xl md:text-3xl mb-3">MusAgent</h2>
      <p className="text-sm mb-8 font-cjk" style={{ color: 'var(--text-secondary)' }}>
        文学灵感生成 · 诗词检索 · 创作润色
      </p>
      <p className="text-xs font-cjk" style={{ color: 'var(--text-muted)' }}>
        联系：lsq1783198384@icloud.com ·
        <Link to={ROUTES.knowledgeGraph.path} className="text-yellow ml-1 hover:underline">关系图谱</Link>
      </p>
    </div>
  </footer>
);

export default Contact;
