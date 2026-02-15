# Component Library Usage Guide

Complete guide for all VoiceClone AI React components.

## UI Components

### Button
```tsx
import { Button } from '@/components/ui';

// Primary button
<Button variant="primary" onClick={handleClick}>
  Save Changes
</Button>

// Secondary button
<Button variant="secondary">Cancel</Button>

// Danger button
<Button variant="danger">Delete</Button>

// Ghost button
<Button variant="ghost">Learn More</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>

// Full width
<Button fullWidth>Submit</Button>

// Loading state
<Button loading>Processing...</Button>
```

### Card
```tsx
import { Card } from '@/components/ui';

// Basic card
<Card>
  <p>Card content here</p>
</Card>

// Card with title
<Card title="Settings">
  <p>Card content here</p>
</Card>

// Card with footer
<Card
  title="Voice Profile"
  footer={
    <Button variant="primary">Save Profile</Button>
  }
>
  <p>Card content here</p>
</Card>
```

### Input
```tsx
import { Input } from '@/components/ui';

// Basic input
<Input
  placeholder="Enter your name"
  value={name}
  onChange={(e) => setName(e.target.value)}
/>

// Input with label
<Input
  label="Email Address"
  type="email"
  placeholder="you@example.com"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>

// Input with error
<Input
  label="Username"
  value={username}
  error="Username is required"
  onChange={(e) => setUsername(e.target.value)}
/>
```

### Textarea
```tsx
import { Textarea } from '@/components/ui';

// Basic textarea
<Textarea
  placeholder="Enter description"
  value={description}
  onChange={(e) => setDescription(e.target.value)}
/>

// Textarea with label and rows
<Textarea
  label="Voice Description"
  rows={6}
  placeholder="Describe the voice characteristics..."
  value={description}
  onChange={(e) => setDescription(e.target.value)}
/>

// Textarea with error
<Textarea
  label="Notes"
  error="Notes cannot be empty"
  value={notes}
  onChange={(e) => setNotes(e.target.value)}
/>
```

### Select
```tsx
import { Select } from '@/components/ui';

const options = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
];

// Basic select
<Select
  options={options}
  value={language}
  onChange={setLanguage}
/>

// Select with label
<Select
  label="Language"
  options={options}
  value={language}
  onChange={setLanguage}
/>

// Select with placeholder
<Select
  label="Voice Model"
  placeholder="Choose a model..."
  options={modelOptions}
  value={model}
  onChange={setModel}
/>

// Select with error
<Select
  label="Output Format"
  options={formatOptions}
  value={format}
  error="Format is required"
  onChange={setFormat}
/>
```

### ProgressBar
```tsx
import { ProgressBar } from '@/components/ui';

// Basic progress
<ProgressBar progress={45} />

// Progress with label
<ProgressBar
  progress={75}
  label="Processing audio"
/>

// Progress with percentage
<ProgressBar
  progress={60}
  label="Cloning voice"
  showPercentage
/>

// Indeterminate progress
<ProgressBar indeterminate label="Loading..." />
```

### StatusBadge
```tsx
import { StatusBadge } from '@/components/ui';

// Success badge
<StatusBadge status="success">Completed</StatusBadge>

// Error badge
<StatusBadge status="error">Failed</StatusBadge>

// Warning badge
<StatusBadge status="warning">Processing</StatusBadge>

// Info badge
<StatusBadge status="info">New</StatusBadge>

// Pending badge
<StatusBadge status="pending">Queued</StatusBadge>

// Without dot
<StatusBadge status="success" withDot={false}>
  Active
</StatusBadge>
```

### Modal
```tsx
import { Modal } from '@/components/ui';
import { useState } from 'react';

const [isOpen, setIsOpen] = useState(false);

// Basic modal
<Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
  <p>Modal content here</p>
</Modal>

// Modal with title
<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Delete Voice Profile"
>
  <p>Are you sure you want to delete this profile?</p>
  <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
    <Button variant="danger">Delete</Button>
    <Button variant="secondary" onClick={() => setIsOpen(false)}>
      Cancel
    </Button>
  </div>
</Modal>

// Modal sizes
<Modal size="sm" isOpen={isOpen} onClose={handleClose}>...</Modal>
<Modal size="md" isOpen={isOpen} onClose={handleClose}>...</Modal>
<Modal size="lg" isOpen={isOpen} onClose={handleClose}>...</Modal>
```

### Tabs
```tsx
import { Tabs } from '@/components/ui';
import { useState } from 'react';

const tabs = [
  { id: 'clone', label: 'Clone Voice' },
  { id: 'tts', label: 'Text-to-Speech' },
  { id: 'history', label: 'History' },
];

const [activeTab, setActiveTab] = useState('clone');

<Tabs
  tabs={tabs}
  activeTab={activeTab}
  onChange={setActiveTab}
/>

// Use with TabContainer
<Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
{activeTab === 'clone' && (
  <TabContainer id="tabpanel-clone">
    <CloneVoiceContent />
  </TabContainer>
)}
{activeTab === 'tts' && (
  <TabContainer id="tabpanel-tts">
    <TTSContent />
  </TabContainer>
)}
```

### Toast with useToast Hook
```tsx
import { ToastContainer } from '@/components/ui';
import { useToast } from '@/hooks/useToast';

function App() {
  const { toasts, dismissToast, success, error, warning, info } = useToast();

  const handleSuccess = () => {
    success('Voice cloned successfully!', 'Success');
  };

  const handleError = () => {
    error('Failed to process audio', 'Error', 7000);
  };

  const handleWarning = () => {
    warning('Audio quality is low', 'Warning');
  };

  const handleInfo = () => {
    info('Processing may take a few minutes', 'Info');
  };

  return (
    <>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <Button onClick={handleSuccess}>Show Success</Button>
      <Button onClick={handleError}>Show Error</Button>
      <Button onClick={handleWarning}>Show Warning</Button>
      <Button onClick={handleInfo}>Show Info</Button>
    </>
  );
}
```

## Audio Components

### AudioPlayer
```tsx
import { AudioPlayer } from '@/components/audio';

// Basic audio player
<AudioPlayer src="/audio/sample.wav" />

// With autoplay
<AudioPlayer src={audioUrl} autoPlay />
```

## Layout Components

### Header
```tsx
import { Header } from '@/components/layout';

<Header onSettingsClick={() => setSettingsOpen(true)} />
```

### MainLayout
```tsx
import { MainLayout, Header } from '@/components/layout';

function App() {
  return (
    <>
      <Header onSettingsClick={handleSettings} />
      <MainLayout>
        {/* Your app content */}
      </MainLayout>
    </>
  );
}
```

### TabContainer
```tsx
import { TabContainer } from '@/components/layout';

<TabContainer id="tabpanel-clone">
  <p>Tab content here</p>
</TabContainer>
```

## Complete Example

```tsx
import { useState } from 'react';
import {
  Header,
  MainLayout,
  Card,
  Button,
  Input,
  Textarea,
  Select,
  ProgressBar,
  StatusBadge,
  Modal,
  Tabs,
  TabContainer,
  ToastContainer,
} from '@/components';
import { AudioPlayer } from '@/components/audio';
import { useToast } from '@/hooks/useToast';

const tabs = [
  { id: 'clone', label: 'Clone Voice' },
  { id: 'tts', label: 'Text-to-Speech' },
  { id: 'history', label: 'History' },
];

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
];

function App() {
  const [activeTab, setActiveTab] = useState('clone');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [progress, setProgress] = useState(0);

  const { toasts, dismissToast, success, error } = useToast();

  const handleClone = () => {
    success('Voice cloning started!');
    // Start cloning process
  };

  return (
    <>
      <Header onSettingsClick={() => setSettingsOpen(true)} />
      <MainLayout>
        <Card>
          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === 'clone' && (
            <TabContainer id="tabpanel-clone">
              <h2>Clone Your Voice</h2>
              <Input
                label="Voice Name"
                placeholder="My Voice Profile"
              />
              <Select
                label="Language"
                options={languageOptions}
                value={language}
                onChange={setLanguage}
              />
              <Textarea
                label="Description"
                placeholder="Describe the voice..."
                rows={4}
              />
              <ProgressBar
                progress={progress}
                label="Processing"
                showPercentage
              />
              <Button fullWidth onClick={handleClone}>
                Start Cloning
              </Button>
            </TabContainer>
          )}

          {activeTab === 'tts' && (
            <TabContainer id="tabpanel-tts">
              <h2>Text-to-Speech</h2>
              <Textarea
                label="Text"
                placeholder="Enter text to synthesize..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={6}
              />
              <Button variant="primary">Generate Speech</Button>
            </TabContainer>
          )}

          {activeTab === 'history' && (
            <TabContainer id="tabpanel-history">
              <h2>Generation History</h2>
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <div>
                    <h3>Sample Audio</h3>
                    <StatusBadge status="success">Completed</StatusBadge>
                  </div>
                </div>
                <AudioPlayer src="/audio/sample.wav" />
              </Card>
            </TabContainer>
          )}
        </Card>

        <Modal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          title="Settings"
          size="md"
        >
          <p>Settings content here</p>
        </Modal>
      </MainLayout>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </>
  );
}

export default App;
```

## Accessibility Features

All components include:
- ARIA labels and roles
- Keyboard navigation support
- Focus management
- Screen reader compatibility
- Semantic HTML structure
- Color contrast compliance

## Styling

Components use CSS custom properties from `variables.css`:
- `--bg-primary`, `--bg-card`, `--bg-card-hover`
- `--text-primary`, `--text-secondary`, `--text-muted`
- `--accent`, `--accent-hover`, `--accent-subtle`
- `--success`, `--error`, `--warning`
- `--border`, `--border-light`
- `--radius-sm`, `--radius`, `--radius-lg`
- `--shadow`, `--shadow-sm`
- `--transition`

## Responsive Design

All components are mobile-responsive with breakpoints:
- Mobile: < 640px
- Tablet: 640px - 768px
- Desktop: > 768px
