import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Plus, 
  MessageSquare, 
  Paperclip, 
  Send, 
  Zap, 
  BookOpen, 
  Scroll, 
  Settings, 
  MoreHorizontal, 
  ChevronRight, 
  Sparkles, 
  Layers, 
  FileText 
} from 'lucide-react';

// --- 动画关键帧 ---
const animations = `
  @keyframes float {
    0% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-20px) rotate(5deg); }
    100% { transform: translateY(0px) rotate(0deg); }
  }
  @keyframes blob-movement {
    0% { border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%; }
    34% { border-radius: 70% 30% 50% 50% / 30% 30% 70% 70%; }
    67% { border-radius: 100% 60% 60% 100% / 100% 100% 60% 60%; }
    100% { border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%; }
  }
  @keyframes pulse-gold {
    0%, 100% { box-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
    50% { box-shadow: 0 0 25px rgba(212, 175, 55, 0.6); }
  }
  @keyframes leaf-fall {
    0% { transform: translate(0, -10%) rotate(0deg); opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { transform: translate(100px, 110vh) rotate(360deg); opacity: 0; }
  }
`;

const App = () => {
  const [messages, setMessages] = useState([
    { id: 1, role: 'ai', content: '欢迎来到奥利凡德的思维工坊。今天想探寻哪种魔法知识？', timestamp: '10:00' },
    { id: 2, role: 'user', content: '帮我设计一个关于魔法药水的配方。', timestamp: '10:02' },
  ]);
  const [inputText, setInputText] = useState('');
  const [isDeepThinking, setIsDeepThinking] = useState(false);
  const [artifacts, setArtifacts] = useState([
    { id: 1, title: '生骨灵药方 v1.2', type: 'scroll', date: '2023-10-27' },
    { id: 2, title: '活点地图底层逻辑', type: 'code', date: '2023-10-28' }
  ]);

  // 背景粒子模拟
  const particles = Array.from({ length: 15 });

  const handleSend = () => {
    if (!inputText.trim()) return;
    const newMsg = { 
      id: Date.now(), 
      role: 'user', 
      content: inputText, 
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    };
    setMessages([...messages, newMsg]);
    setInputText('');
    
    // 模拟AI回复
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'ai',
        content: isDeepThinking ? "正在翻阅禁书区... 这是一份经过深层逻辑推理的古老配方。" : "这是一份基础的药水配方。",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }, 1000);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#fdfbf7] font-serif text-[#4a3f35] relative">
      <style>{animations}</style>

      {/* --- 魔法动态背景 --- */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* 液态背景块 */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#f5e6d3] opacity-30 blur-[100px]" style={{ animation: 'blob-movement 20s infinite alternate linear' }}></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#e3f2fd] opacity-40 blur-[120px]" style={{ animation: 'blob-movement 25s infinite alternate-reverse linear' }}></div>
        
        {/* 飘落的花瓣/粒子 */}
        {particles.map((_, i) => (
          <div 
            key={i}
            className="absolute bg-white/60 rounded-full blur-[1px]"
            style={{
              left: `${Math.random() * 100}%`,
              width: `${Math.random() * 8 + 4}px`,
              height: `${Math.random() * 12 + 6}px`,
              top: '-5%',
              animation: `leaf-fall ${Math.random() * 10 + 10}s linear infinite`,
              animationDelay: `${Math.random() * 10}s`,
              opacity: 0.4
            }}
          ></div>
        ))}
      </div>

      {/* --- 左侧：历史记忆 (The Hall of Memories) --- */}
      <aside className="w-72 flex flex-col z-10 border-r border-[#e8dcc4] bg-white/20 backdrop-blur-2xl">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-[#d4af37] to-[#aa8c2c] rounded-full flex items-center justify-center shadow-lg">
            <BookOpen className="text-white w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#2c241d] italic">Pensieve</h1>
        </div>

        <div className="px-4 mb-4">
          <button className="w-full py-3 px-4 rounded-xl bg-[#f5efe1] border border-[#d4af37]/30 flex items-center justify-center gap-2 hover:bg-[#eaddc0] transition-all group shadow-sm">
            <Plus className="w-4 h-4 text-[#d4af37] group-hover:rotate-90 transition-transform" />
            <span className="text-sm font-semibold">开启新篇章</span>
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 space-y-1">
          <div className="px-4 py-2 text-[10px] uppercase tracking-[0.2em] text-[#a08b73] font-bold">近期回溯</div>
          {['关于凤凰羽毛的论文', '海格的小屋扩建计划', '卢莫斯咒语改进'].map((chat, i) => (
            <div 
              key={i} 
              className={`group flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all hover:bg-[#fcf8ef] ${i === 0 ? 'bg-[#fcf8ef] border-l-4 border-[#d4af37]' : ''}`}
            >
              <MessageSquare className="w-4 h-4 text-[#a08b73]" />
              <span className="text-sm truncate opacity-80">{chat}</span>
            </div>
          ))}
        </nav>

        <div className="p-4 border-t border-[#e8dcc4] flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#333] border-2 border-[#d4af37] overflow-hidden">
             <div className="w-full h-full bg-gradient-to-tr from-indigo-200 to-amber-100 flex items-center justify-center text-[10px] text-gray-700">HP</div>
          </div>
          <div className="flex-1">
            <p className="text-xs font-bold">哈利·波特</p>
            <p className="text-[10px] opacity-50">格兰芬多学院</p>
          </div>
          <Settings className="w-4 h-4 opacity-40 hover:opacity-100 cursor-pointer" />
        </div>
      </aside>

      {/* --- 中间：主聊天区域 (The Chamber of Dialogue) --- */}
      <main className="flex-1 flex flex-col z-10 relative">
        {/* 顶部工具栏 */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-[#e8dcc4] bg-white/10 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-sm font-medium opacity-70">魔法核心已就绪</span>
          </div>

          {/* 深度思考开关 (Golden Snitch Toggle) */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold tracking-wider text-[#a08b73]">深度思考</span>
            <button 
              onClick={() => setIsDeepThinking(!isDeepThinking)}
              className={`w-14 h-7 rounded-full relative transition-all duration-500 overflow-hidden ${isDeepThinking ? 'bg-[#d4af37]' : 'bg-[#e2e2e2]'}`}
            >
              <div 
                className={`absolute top-1 w-5 h-5 rounded-full transition-all duration-500 flex items-center justify-center ${isDeepThinking ? 'left-8 bg-white rotate-[360deg]' : 'left-1 bg-white'}`}
                style={{ boxShadow: isDeepThinking ? '0 0 10px white' : 'none' }}
              >
                <Zap className={`w-3 h-3 ${isDeepThinking ? 'text-[#d4af37]' : 'text-gray-300'}`} />
              </div>
            </button>
          </div>
        </header>

        {/* 消息展示区 */}
        <section className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] group ${msg.role === 'user' ? 'order-1' : ''}`}>
                <div className={`
                  relative p-5 rounded-3xl shadow-sm border transition-transform hover:scale-[1.01]
                  ${msg.role === 'user' 
                    ? 'bg-[#f5efe1] border-[#d4af37]/20 rounded-tr-none text-[#4a3f35]' 
                    : 'bg-white/60 backdrop-blur-xl border-white/40 rounded-tl-none text-[#2c241d]'}
                `}>
                  {msg.role === 'ai' && (
                    <div className="absolute -top-4 -left-2 bg-white rounded-full p-1 shadow-md border border-[#eee]">
                       <Sparkles className="w-3 h-3 text-[#d4af37]" />
                    </div>
                  )}
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                </div>
                <div className={`text-[10px] mt-2 opacity-30 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))}
        </section>

        {/* 输入区域 */}
        <footer className="p-8 pt-0 bg-transparent">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-[#d4af37]/20 via-[#e8dcc4]/20 to-[#d4af37]/20 rounded-[2rem] blur opacity-30 group-hover:opacity-60 transition duration-1000"></div>
            {/* 输入框容器：增加了 focus-within 状态下的金色阴影和边框色 */}
            <div className="relative bg-white/70 backdrop-blur-2xl rounded-[1.8rem] border border-[#e8dcc4] shadow-2xl flex items-end p-2 pr-4 min-h-[64px] transition-all duration-300 focus-within:border-[#d4af37]/50 focus-within:shadow-[0_0_20px_rgba(212,175,55,0.15)]">
              
              {/* 文件上传 (Wax Seal style) */}
              <button className="p-3 hover:bg-[#fdfbf7] rounded-full transition-colors group/upload relative">
                <Paperclip className="w-5 h-5 text-[#a08b73]" />
                <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#4a3f35] text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover/upload:opacity-100 transition-opacity whitespace-nowrap">
                  上传附件
                </div>
              </button>

              {/* Textarea：去除了 outline-none 和默认蓝色环绕 */}
              <textarea 
                rows="1"
                placeholder="在此书写您的智慧..."
                className="flex-1 bg-transparent border-none focus:ring-0 outline-none text-sm py-4 px-2 resize-none placeholder-[#a08b73]/50 text-[#4a3f35]"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />

              <button 
                onClick={handleSend}
                className={`p-3 rounded-2xl transition-all ${inputText ? 'bg-[#d4af37] text-white shadow-lg' : 'bg-gray-100 text-gray-300'}`}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
          <p className="text-center mt-4 text-[10px] opacity-40 uppercase tracking-widest text-[#a08b73]">魔法并非万能，请保持理性思考</p>
        </footer>
      </main>

      {/* --- 右侧：Artifact 成果展示 (The Archive of Spells) --- */}
      <aside className="w-80 flex flex-col z-10 border-l border-[#e8dcc4] bg-white/30 backdrop-blur-2xl">
        <div className="p-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-lg font-bold italic text-[#2c241d] flex items-center gap-2">
              <Scroll className="w-5 h-5 text-[#d4af37]" />
              真理印记
            </h2>
            <div className="flex gap-1">
               <div className="w-2 h-2 rounded-full bg-[#d4af37]/20"></div>
               <div className="w-2 h-2 rounded-full bg-[#d4af37]/40"></div>
               <div className="w-2 h-2 rounded-full bg-[#d4af37]/60"></div>
            </div>
          </div>

          <div className="space-y-4">
            {artifacts.map((art) => (
              <div 
                key={art.id} 
                className="group relative bg-[#fdfbf7] p-4 rounded-2xl border border-[#e8dcc4] hover:border-[#d4af37] transition-all cursor-pointer overflow-hidden"
                style={{ animation: 'float 6s infinite ease-in-out', animationDelay: `${art.id}s` }}
              >
                {/* 装饰用的小背景图腾 */}
                <div className="absolute -right-4 -bottom-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
                   <Layers size={100} />
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 bg-white rounded-lg shadow-sm">
                    {art.type === 'scroll' ? <FileText className="w-4 h-4 text-[#d4af37]" /> : <Zap className="w-4 h-4 text-blue-400" />}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold opacity-80 group-hover:text-[#d4af37] transition-colors">{art.title}</h3>
                    <p className="text-[10px] opacity-40 mt-1 uppercase font-semibold">{art.date}</p>
                  </div>
                </div>

                <div className="mt-4 flex justify-between items-center">
                   <div className="flex -space-x-2">
                      {[1,2,3].map(i => (
                        <div key={i} className="w-5 h-5 rounded-full border border-white bg-gray-200 overflow-hidden">
                           <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-300"></div>
                        </div>
                      ))}
                   </div>
                   <button className="text-[10px] font-bold text-[#d4af37] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      查看详情 <ChevronRight className="w-3 h-3" />
                   </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-12 p-6 rounded-3xl bg-gradient-to-br from-[#d4af37]/10 to-transparent border border-[#d4af37]/20">
             <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#d4af37]" />
                <span className="text-xs font-bold uppercase tracking-wider">智力加成</span>
             </div>
             <p className="text-[11px] leading-relaxed opacity-60 italic text-[#4a3f35]">
               "在这个空间内，所有的中间产物都将被永恒记录。每一个咒语的改动都是通往伟大的阶梯。"
             </p>
          </div>
        </div>
      </aside>
    </div>
  );
};

export default App;