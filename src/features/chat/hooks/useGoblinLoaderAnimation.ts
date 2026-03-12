import { useEffect, useState } from 'react';

type LottieAnimationData = Record<string, unknown>;

const useGoblinLoaderAnimation = () => {
  const [animationData, setAnimationData] = useState<LottieAnimationData | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const loadAnimation = async () => {
      try {
        const response = await fetch('/goblin_loader.json', {
          signal: controller.signal,
        });
        if (!response.ok) return;
        const data = await response.json();
        if (mounted) {
          setAnimationData(data);
        }
      } catch (error) {
        if ((error as Error).name === 'AbortError') return;
      }
    };

    void loadAnimation();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  return animationData;
};

export default useGoblinLoaderAnimation;
