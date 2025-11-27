import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';
import { initDatadog } from './utils/datadog-rum';
import { setupGlobalErrorTracking, monitorNetworkStatus } from './utils/error-tracking';

// Initialize Datadog RUM and Browser Logs for production monitoring
initDatadog();

// Setup global error tracking and network monitoring
setupGlobalErrorTracking();
monitorNetworkStatus();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary componentName="App">
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
