import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const Lottie = dynamic(() => import('lottie-react'), { ssr: false });

interface GoblinLoaderProps {
  size?: number;
  className?: string;
}

const GoblinLoader = ({ size = 96, className = '' }: GoblinLoaderProps) => {
  const [animationData, setAnimationData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let mounted = true;
    fetch('/goblin_loader.json')
      .then(response => (response.ok ? response.json() : null))
      .then(data => {
        if (mounted && data) setAnimationData(data);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div
      className={`flex items-center justify-center rounded-2xl ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {animationData ? (
        <Lottie animationData={animationData} loop />
      ) : (
        <div className="h-full w-full rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-3xl">
          🧠
        </div>
      )}
    </div>
  );
};

export default GoblinLoader;
