/**
 * Main Application Component
 *
 * VoiceClone AI - Complete React Frontend
 */

import { useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { Tabs } from '@/components/ui/Tabs';
import { ToastContainer } from '@/components/ui/Toast';
import { VoiceReplace } from '@/features/voice-replace/VoiceReplace';
import { TTS } from '@/features/tts/TTS';
import { Music } from '@/features/music/Music';
import { RealtimeVoiceChanger } from '@/features/realtime/RealtimeVoiceChanger';
import { AudioMixer } from '@/features/mixer/AudioMixer';
import { Singing } from '@/features/singing/Singing';
import { Sidebar } from '@/features/sidebar/Sidebar';
import { Settings } from '@/features/settings/Settings';
import { useUIStore } from '@/store/uiStore';
import { useJobStore } from '@/store/jobStore';
import './App.css';

function App() {
  const { activeTab, setActiveTab, isSettingsOpen, openSettings, closeSettings } = useUIStore();
  const { refreshJobs } = useJobStore();

  // Load jobs on mount
  useEffect(() => {
    refreshJobs();
  }, [refreshJobs]);

  const tabs = [
    { id: 'voice-replace', label: 'Voice Replace' },
    { id: 'tts', label: 'Text-to-Speech' },
    { id: 'music', label: 'Music Generation' },
    { id: 'mixer', label: 'Audio Mixer' },
    { id: 'singing', label: 'Singing Synthesis' },
    { id: 'realtime', label: 'Voice Changer' },
  ];

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabs.findIndex((t) => t.id === tabId));
  };

  const getCurrentTabId = () => tabs[activeTab]?.id || 'voice-replace';

  return (
    <>
      <div className="app-layout">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <div className="app-main">
          {/* Header */}
          <Header onSettingsClick={openSettings} />

          {/* Tab Navigation */}
          <Tabs
            tabs={tabs.map((t) => ({ id: t.id, label: t.label }))}
            activeTab={getCurrentTabId()}
            onChange={handleTabChange}
          />

          {/* Tab Content */}
          <main className="app-content">
            {getCurrentTabId() === 'voice-replace' && <VoiceReplace />}
            {getCurrentTabId() === 'tts' && <TTS />}
            {getCurrentTabId() === 'music' && <Music />}
            {getCurrentTabId() === 'mixer' && <AudioMixer />}
            {getCurrentTabId() === 'singing' && <Singing />}
            {getCurrentTabId() === 'realtime' && <RealtimeVoiceChanger />}
          </main>
        </div>
      </div>

      {/* Settings Modal */}
      <Settings isOpen={isSettingsOpen} onClose={closeSettings} />

      {/* Toast Notifications */}
      <ToastContainer />
    </>
  );
}

export default App;
