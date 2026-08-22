import React, { useState } from 'react';

export default function App() {
  const [plcStatus, setPlcStatus] = useState('RUNNING');

  const handlePause = () => setPlcStatus('PAUSED');
  const handleContinue = () => setPlcStatus('RUNNING');
  const handleReset = () => console.log('Resetting Lote...');

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#0d1117] text-[#c9d1d9] p-3 md:p-4 flex items-center justify-center font-mono text-xs md:text-sm leading-tight select-none">
      
      {/* Main Container */}
      <div className="w-full h-full max-w-4xl border border-[#30363d] bg-[#0d1117] p-3 md:p-4 shadow-2xl relative flex flex-col justify-between overflow-hidden">
        
        {/* Header */}
        <div className="flex-none flex justify-between items-center border-b border-[#30363d] pb-2 mb-2">
          <span className="tracking-widest font-bold">ESTEIRA 01</span>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">PLC SIMULADO:</span>
            <div className={`w-2 h-2 rounded-full ${plcStatus === 'RUNNING' ? 'bg-green-500' : 'bg-red-500 animate-pulse'}`}></div>
            <span className={plcStatus === 'RUNNING' ? 'text-green-500' : 'text-red-500'}>{plcStatus}</span>
          </div>
        </div>

        {/* Main Content Area - Stacked Vertically */}
        <div className="flex-grow flex flex-col justify-evenly gap-3 border-b border-[#30363d] pb-2 min-h-0 overflow-hidden">
          
          {/* Top Section: Video Container - Controlled Max Width/Height */}
          <div className="w-full flex justify-center items-center flex-1 min-h-0">
            <div className="w-full max-w-[450px] aspect-video border border-dashed border-[#30363d] flex flex-col items-center justify-center opacity-70 my-auto">
                <span>VÍDEO ANOTADO (16:9)</span>
                <span className="text-gray-500 text-[10px] md:text-xs mt-2">mask + ID + confidence</span>
            </div>
          </div>

          {/* Bottom Section: Information Grid - 3 Columns */}
          <div className="w-full grid grid-cols-3 gap-3 flex-none">
            
            {/* Lote Atual Box */}
            <div className="border border-[#30363d] p-2.5 flex flex-col justify-center">
              <span className="text-gray-400 mb-1 font-bold uppercase block text-center border-b border-[#30363d] pb-1 text-xs">Lote Atual</span>
              <div className="space-y-0.5 mt-1 text-xs">
                <div className="flex justify-between"><span>Peças:</span> <span className="text-white">37</span></div>
                <div className="flex justify-between"><span>Volume:</span> <span className="text-white">291.4 L</span></div>
                <div className="flex justify-between"><span>CI95:</span> <span className="text-white">285-299 L</span></div>
                <div className="flex justify-between"><span>Duplicações:</span> <span className="text-green-400">0</span></div>
              </div>
            </div>

            {/* Battery Tracking Box */}
            <div className="border border-[#30363d] p-2.5 flex flex-col justify-center">
              <span className="text-blue-400 mb-1 font-bold uppercase block text-center border-b border-[#30363d] pb-1 text-xs">Battery #0017</span>
              <div className="space-y-0.5 mt-1 text-xs">
                <div className="flex justify-between"><span>Volume:</span> <span className="text-white">7.94 L</span></div>
                <div className="flex justify-between"><span>CI95:</span> <span className="text-white">7.41-8.05 L</span></div>
                <div className="flex justify-between"><span>Confidence:</span> <span className="text-white">83%</span></div>
                <div className="flex justify-between"><span>State:</span> <span className="text-yellow-400">TRACKING</span></div>
              </div>
            </div>

            {/* Generalization Box */}
            <div className="border border-[#30363d] p-2.5 flex flex-col justify-center">
              <span className="text-gray-400 mb-1 font-bold uppercase block text-center border-b border-[#30363d] pb-1 text-xs">Generalização</span>
              <div className="space-y-0.5 mt-1 text-xs">
                <div className="flex justify-between"><span>1080p:</span> <span className="text-white">291.4 L</span></div>
                <div className="flex justify-between"><span>720p:</span> <span className="text-white">289.9 L</span></div>
                <div className="flex justify-between"><span>Gap:</span> <span className="text-red-400">0.51%</span></div>
              </div>
            </div>
            
          </div>
        </div>

        {/* Footer: VLM and Controls */}
        <div className="flex-none flex flex-col items-center pt-1 space-y-2">
          <div className="w-full text-center text-gray-400 truncate text-xs">
            VLM: <span className="italic text-gray-300">"A bateria #17 foi reassociada após oclusão..."</span>
          </div>
          
          <div className="flex gap-6 text-gray-500 font-bold text-xs">
            <button onClick={handlePause} className="hover:text-white transition-colors">[PAUSAR]</button>
            <button onClick={handleContinue} className="hover:text-white transition-colors">[CONTINUAR]</button>
            <button onClick={handleReset} className="hover:text-white transition-colors">[RESET LOTE]</button>
          </div>
        </div>

      </div>
    </div>
  );
}