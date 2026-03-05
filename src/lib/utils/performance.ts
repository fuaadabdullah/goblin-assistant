// Performance optimization utilities

// Performance monitoring
export class PerformanceMonitor {
  private static measurements: Map<string, number> = new Map();

  static start(name: string): void {
    this.measurements.set(name, performance.now());
  }

  static end(name: string): number {
    const startTime = this.measurements.get(name);
    if (!startTime) {
      console.warn(`Performance measurement "${name}" was not started`);
      return 0;
    }
    
    const duration = performance.now() - startTime;
    this.measurements.delete(name);
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`⏱️ ${name}: ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }

  static measure<T>(name: string, fn: () => T): T {
    this.start(name);
    const result = fn();
    this.end(name);
    return result;
  }

  static async measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
    this.start(name);
    const result = await fn();
    this.end(name);
    return result;
  }
}

// Virtualization utilities
export interface VirtualizationConfig {
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
}

export interface VirtualizationResult {
  startIndex: number;
  endIndex: number;
  visibleItems: any[];
  totalHeight: number;
  offsetY: number;
}

export const calculateVirtualization = (
  items: any[],
  scrollTop: number,
  config: VirtualizationConfig
): VirtualizationResult => {
  const { itemHeight, containerHeight, overscan = 5 } = config;
  
  const totalHeight = items.length * itemHeight;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  );
  
  const visibleItems = items.slice(startIndex, endIndex + 1);
  const offsetY = startIndex * itemHeight;
  
  return {
    startIndex,
    endIndex,
    visibleItems,
    totalHeight,
    offsetY,
  };
};

// Lazy loading utilities
export const lazyLoadImage = (imgElement: HTMLImageElement): Promise<void> => {
  return new Promise((resolve, reject) => {
    if ('loading' in HTMLImageElement.prototype) {
      // Native lazy loading supported
      imgElement.loading = 'lazy';
      imgElement.onload = () => resolve();
      imgElement.onerror = () => reject(new Error('Image failed to load'));
    } else {
      // Fallback for older browsers
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const lazyImage = entry.target as HTMLImageElement;
            lazyImage.src = lazyImage.dataset.src || '';
            lazyImage.classList.remove('lazy');
            observer.unobserve(lazyImage);
            resolve();
          }
        });
      });
      
      observer.observe(imgElement);
    }
  });
};

// Resource preloading
export const preloadResource = (url: string, type: 'image' | 'script' | 'style'): Promise<void> => {
  return new Promise((resolve, reject) => {
    let element: HTMLElement;
    
    switch (type) {
      case 'image':
        element = new Image();
        (element as HTMLImageElement).src = url;
        break;
      case 'script':
        element = document.createElement('script');
        (element as HTMLScriptElement).src = url;
        break;
      case 'style':
        element = document.createElement('link');
        (element as HTMLLinkElement).rel = 'stylesheet';
        (element as HTMLLinkElement).href = url;
        break;
    }
    
    element.onload = () => resolve();
    element.onerror = () => reject(new Error(`Failed to preload ${type}: ${url}`));
    
    if (type !== 'image') {
      document.head.appendChild(element);
    }
  });
};

// Memory management
export const cleanupMemory = (): void => {
  // Clear unused timers
  for (let i = 0; i < 10000; i++) {
    clearTimeout(i);
    clearInterval(i);
  }
  
  // Clear service workers (development only)
  if (process.env.NODE_ENV === 'development' && 'serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      registrations.forEach((registration) => {
        registration.unregister();
      });
    });
  }
  
  // Force garbage collection if available
  if ((window as any).gc) {
    (window as any).gc();
  }
};

// Bundle analysis utilities
export const analyzeBundle = (): void => {
  if (process.env.NODE_ENV !== 'development') return;
  
  // Log all modules
  if ((window as any).__webpack_modules__) {
    const modules = Object.keys((window as any).__webpack_modules__);
    console.group('📦 Bundle Analysis');
    console.log(`Total modules: ${modules.length}`);
    
    // Group by package
    const packages: Record<string, number> = {};
    modules.forEach((module) => {
      const match = module.match(/node_modules[\/\\]([^/\\]+)\/?/);
      if (match) {
        const pkg = match[1];
        packages[pkg] = (packages[pkg] || 0) + 1;
      }
    });
    
    console.table(packages);
    console.groupEnd();
  }
};

// FPS monitoring
export class FPSMonitor {
  private frames: number[] = [];
  private rafId: number | null = null;
  private lastTime: number = performance.now();
  private onFPSUpdate: (fps: number) => void;

  constructor(onFPSUpdate: (fps: number) => void) {
    this.onFPSUpdate = onFPSUpdate;
  }

  start(): void {
    if (this.rafId) return;
    
    const measure = (currentTime: number) => {
      const delta = currentTime - this.lastTime;
      this.lastTime = currentTime;
      
      const fps = 1000 / delta;
      this.frames.push(fps);
      
      // Keep only last 60 frames
      if (this.frames.length > 60) {
        this.frames.shift();
      }
      
      // Calculate average FPS
      const avgFPS = this.frames.reduce((sum, frame) => sum + frame, 0) / this.frames.length;
      this.onFPSUpdate(Math.round(avgFPS));
      
      this.rafId = requestAnimationFrame(measure);
    };
    
    this.rafId = requestAnimationFrame(measure);
  }

  stop(): void {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }
}

// Critical resource monitoring
export const monitorCriticalResources = (): void => {
  if (process.env.NODE_ENV !== 'development') return;
  
  const observer = new PerformanceObserver((list) => {
    list.getEntries().forEach((entry) => {
      if (entry.entryType === 'navigation') {
        const nav = entry as PerformanceNavigationTiming;
        console.group('🚀 Navigation Timing');
        console.log(`DNS Lookup: ${nav.domainLookupEnd - nav.domainLookupStart}ms`);
        console.log(`TCP Connect: ${nav.connectEnd - nav.connectStart}ms`);
        console.log(`SSL Negotiation: ${nav.secureConnectionStart > 0 ? nav.connectEnd - nav.secureConnectionStart : 0}ms`);
        console.log(`TTFB: ${nav.responseStart - nav.requestStart}ms`);
        console.log(`Download: ${nav.responseEnd - nav.responseStart}ms`);
        console.log(`DOM Parse: ${nav.domContentLoadedEventStart - nav.responseEnd}ms`);
        console.log(`Total Load: ${nav.loadEventEnd - performance.timeOrigin}ms`);
        console.groupEnd();
      } else if (entry.entryType === 'resource') {
        const resource = entry as PerformanceResourceTiming;
        if (resource.transferSize === 0 && resource.decodedBodySize === 0) {
          console.warn(`⚠️ Resource blocked: ${resource.name}`);
        }
      }
    });
  });
  
  observer.observe({ entryTypes: ['navigation', 'resource'] });
};

// Memory usage monitoring
export const monitorMemoryUsage = (): void => {
  if (process.env.NODE_ENV !== 'development') return;
  
  if ('memory' in performance) {
    const logMemory = () => {
      const memory = (performance as any).memory;
      console.group('🧠 Memory Usage');
      console.log(`Used: ${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`);
      console.log(`Total: ${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`);
      console.log(`Limit: ${(memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB`);
      console.groupEnd();
    };
    
    setInterval(logMemory, 5000);
    logMemory();
  }
};

// Render performance monitoring
export const monitorRenderPerformance = (): void => {
  if (process.env.NODE_ENV !== 'development') return;
  
  let renderCount = 0;
  let lastRenderTime = performance.now();
  
  const observer = new MutationObserver(() => {
    const now = performance.now();
    const timeSinceLastRender = now - lastRenderTime;
    
    if (timeSinceLastRender < 16) {
      console.warn(`⚠️ Frequent re-renders detected: ${timeSinceLastRender.toFixed(2)}ms`);
    }
    
    renderCount++;
    lastRenderTime = now;
    
    if (renderCount % 100 === 0) {
      console.log(`📊 Render count: ${renderCount}`);
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true,
  });
};
