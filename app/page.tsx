"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Cpu, Users, Database, Globe, Star, TrendingUp, MessageSquare, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui';
import { Badge } from '@/components/ui/Badge';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useTranslation } from '@/i18n';

export default function Home() {
  const router = useRouter();
  const [isLoaded, setIsLoaded] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  const handleGetStarted = () => {
    router.push('/chat');
  };

  const handleLearnMore = () => {
    router.push('/chat');
  };

  const features = [
    {
      icon: <Cpu className="w-6 h-6" />,
      title: t('home.features.intelligentRouting.title'),
      description: t('home.features.intelligentRouting.description')
    },
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: t('home.features.privacyFirst.title'),
      description: t('home.features.privacyFirst.description')
    },
    {
      icon: <DollarSign className="w-6 h-6" />,
      title: t('home.features.multiProvider.title'),
      description: t('home.features.multiProvider.description')
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: t('home.features.developerFocused.title'),
      description: t('home.features.developerFocused.description')
    }
  ];

  const useCases = [
    {
      icon: <MessageSquare className="w-8 h-8" />,
      title: t('home.useCases.codeAssistance.title'),
      description: t('home.useCases.codeAssistance.description')
    },
    {
      icon: <Database className="w-8 h-8" />,
      title: t('home.useCases.dataAnalysis.title'),
      description: t('home.useCases.dataAnalysis.description')
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: t('home.useCases.research.title'),
      description: t('home.useCases.research.description')
    }
  ];

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full">
          <div className="absolute top-20 left-10 w-72 h-72 bg-accent-green/10 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute top-40 right-10 w-96 h-96 bg-info/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div className="absolute bottom-20 left-1/3 w-80 h-80 bg-warning/10 rounded-full blur-3xl animate-pulse delay-500"></div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10">
        {/* Navigation */}
        <nav className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between rtl-preserve">
            <div className="flex items-center space-x-4 rtl:space-x-reverse">
              <div className="w-10 h-10 bg-gradient-to-r from-accent-green to-info rounded-xl flex items-center justify-center shadow-lg shadow-accent-green/20">
                <Star className="w-6 h-6 text-bg-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-text-primary font-mono">{t('home.title')}</h1>
                <p className="text-xs text-text-secondary font-mono">{t('home.subtitle')}</p>
              </div>
            </div>
            <div className="hidden md:flex items-center space-x-4 rtl:space-x-reverse">
              <Button variant="ghost" className="text-text-secondary hover:text-text-primary font-mono">
                {t('nav.documentation')}
              </Button>
              <Button variant="ghost" className="text-text-secondary hover:text-text-primary font-mono">
                {t('nav.api')}
              </Button>
              <LanguageSwitcher variant="compact" />
              <Button 
                onClick={handleGetStarted}
                className="bg-accent-green text-bg-primary hover:bg-accent-green-bright font-semibold px-6 py-2 rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-accent-green/25 glow"
              >
                {t('home.getStarted')}
                <ArrowRight className="w-4 h-4 ms-2" />
              </Button>
            </div>
            {/* Mobile Language Switcher */}
            <div className="md:hidden">
              <LanguageSwitcher variant="minimal" />
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <main className="container mx-auto px-6 pb-20">
          <div className="text-center max-w-4xl mx-auto">
            {/* Badge */}
            <Badge variant="outline" className="bg-bg-secondary border-border-subtle text-text-primary mb-6 backdrop-blur-sm font-mono">
              <Star className="w-4 h-4 me-2" />
              {t('home.badge')}
            </Badge>

            {/* Title */}
            <h1 className={`text-5xl md:text-7xl font-bold text-text-primary mb-6 transition-all duration-1000 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            } font-mono`}>
              {t('home.heroTitle')}
              <br />
              <span className="bg-gradient-to-r from-accent-green via-info to-warning bg-clip-text text-transparent">
                {t('home.heroTitleHighlight')}
              </span>
            </h1>

            {/* Subtitle */}
            <p className={`text-xl text-text-secondary mb-12 max-w-2xl mx-auto leading-relaxed transition-all duration-1000 delay-300 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            } font-mono`}>
              {t('home.heroDescription')}
            </p>

            {/* CTA Buttons */}
            <div className={`flex flex-col sm:flex-row gap-4 justify-center items-center transition-all duration-1000 delay-600 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <Button 
                onClick={handleGetStarted}
                size="lg"
                className="bg-accent-green text-bg-primary hover:bg-accent-green-bright font-semibold px-8 py-3 rounded-lg text-lg transition-all duration-300 hover:shadow-xl hover:shadow-accent-green/25 transform hover:-translate-y-1 glow"
              >
                {t('home.startBuilding')}
                <ArrowRight className="w-5 h-5 ms-3" />
              </Button>
              <Button 
                onClick={handleLearnMore}
                variant="outline"
                size="lg"
                className="border-border-medium text-text-primary hover:bg-bg-tertiary font-semibold px-8 py-3 rounded-lg text-lg transition-all duration-300 backdrop-blur-sm font-mono"
              >
                {t('home.viewDashboard')}
              </Button>
            </div>

            {/* Stats */}
            <div className={`grid grid-cols-1 md:grid-cols-3 gap-8 mt-16 transition-all duration-1000 delay-900 ${
              isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
            }`}>
              <div className="text-center group hover:bg-bg-tertiary p-6 rounded-xl transition-all duration-300">
                <div className="text-3xl font-bold text-accent-green mb-2">100%</div>
                <div className="text-text-secondary text-sm font-mono">{t('home.stats.privacyFirst')}</div>
              </div>
              <div className="text-center group hover:bg-bg-tertiary p-6 rounded-xl transition-all duration-300">
                <div className="text-3xl font-bold text-info mb-2">Multi</div>
                <div className="text-text-secondary text-sm font-mono">{t('home.stats.multiProvider')}</div>
              </div>
              <div className="text-center group hover:bg-bg-tertiary p-6 rounded-xl transition-all duration-300">
                <div className="text-3xl font-bold text-warning mb-2">Smart</div>
                <div className="text-text-secondary text-sm font-mono">{t('home.stats.smartRouting')}</div>
              </div>
            </div>
          </div>
        </main>

        {/* Features Section */}
        <section className="container mx-auto px-6 pb-20">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="bg-bg-secondary border border-border-subtle rounded-xl p-6 hover:bg-bg-tertiary transition-all duration-300 group hover:-translate-y-2"
              >
                <div className="w-12 h-12 bg-gradient-to-r from-accent-green/20 to-info/20 rounded-xl flex items-center justify-center mb-4 group-hover:from-accent-green/40 group-hover:to-info/40 transition-all duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-text-primary mb-2 font-mono">{feature.title}</h3>
                <p className="text-text-secondary text-sm leading-relaxed font-mono">{feature.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Use Cases Section */}
        <section className="container mx-auto px-6 pb-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-text-primary mb-4 font-mono">{t('home.useCases.title')}</h2>
            <p className="text-text-secondary text-lg font-mono">{t('home.useCases.subtitle')}</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {useCases.map((useCase, index) => (
              <div 
                key={index}
                className="bg-gradient-to-br from-bg-secondary to-bg-tertiary border border-border-medium rounded-2xl p-8 hover:from-bg-tertiary hover:to-bg-elevated transition-all duration-300 group hover:-translate-y-2"
              >
                <div className="w-16 h-16 bg-gradient-to-r from-accent-green/20 to-warning/20 rounded-2xl flex items-center justify-center mb-6 group-hover:from-accent-green/40 group-hover:to-warning/40 transition-all duration-300">
                  {useCase.icon}
                </div>
                <h3 className="text-2xl font-bold text-text-primary mb-4 font-mono">{useCase.title}</h3>
                <p className="text-text-secondary text-lg leading-relaxed font-mono">{useCase.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="container mx-auto px-6 pb-20">
          <div className="bg-gradient-to-r from-accent-green/20 to-info/20 border border-border-medium rounded-3xl p-12 text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-6 font-mono">
              {t('home.cta.title')}
            </h2>
            <p className="text-text-secondary text-lg mb-8 max-w-2xl mx-auto font-mono">
              {t('home.cta.description')}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                onClick={handleGetStarted}
                size="lg"
                className="bg-accent-green text-bg-primary hover:bg-accent-green-bright font-semibold px-10 py-4 rounded-lg text-lg transition-all duration-300 hover:shadow-xl hover:shadow-accent-green/25 transform hover:-translate-y-1 glow"
              >
                {t('home.getStartedFree')}
                <ArrowRight className="w-5 h-5 ms-3" />
              </Button>
              <Button 
                variant="outline"
                size="lg"
                className="border-border-medium text-text-primary hover:bg-bg-tertiary font-semibold px-10 py-4 rounded-lg text-lg transition-all duration-300 backdrop-blur-sm font-mono"
              >
                {t('home.viewLiveDemo')}
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
