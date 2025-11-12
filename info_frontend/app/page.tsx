"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowRight, BarChart3, Brain, Shield, Zap } from "lucide-react";
import Image from "next/image";

export default function Home() {
  const router = useRouter();

  // Auto-redirect after 5 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      router.push("/login");
    }, 5000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="flex flex-col items-center justify-center min-h-[80vh] text-center">
          {/* Logo */}
          <div className="relative w-32 h-32 mb-8 animate-in fade-in zoom-in duration-700">
            <Image
              src="/images/Voila_matita.png"
              alt="Voilà Voice"
              fill
              className="object-contain"
              priority
            />
          </div>

          {/* Heading */}
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6 animate-in slide-in-from-bottom duration-700">
            <span className="bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
              Voilà Voice
            </span>
          </h1>

          <p className="text-xl md:text-2xl text-gray-600 mb-4 max-w-2xl animate-in slide-in-from-bottom duration-700 delay-100">
            Dashboard intelligente per la gestione avanzata del tuo voice agent
          </p>

          <p className="text-sm text-gray-500 mb-12 animate-in slide-in-from-bottom duration-700 delay-200">
            Redirect automatico al login tra 5 secondi...
          </p>

          {/* CTA Button */}
          <Button
            onClick={() => router.push("/login")}
            size="lg"
            className="h-12 px-8 text-lg bg-blue-600 hover:bg-blue-700 animate-in slide-in-from-bottom duration-700 delay-300"
          >
            Accedi alla Dashboard
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>

          {/* Features */}
          <div className="grid md:grid-cols-4 gap-8 mt-20 w-full max-w-4xl animate-in slide-in-from-bottom duration-700 delay-500">
            <div className="flex flex-col items-center space-y-3 p-6 rounded-lg hover:bg-white transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold">Analytics</h3>
              <p className="text-sm text-gray-600 text-center">
                Statistiche in tempo reale
              </p>
            </div>

            <div className="flex flex-col items-center space-y-3 p-6 rounded-lg hover:bg-white transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Brain className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold">AI Knowledge</h3>
              <p className="text-sm text-gray-600 text-center">
                Gestione conoscenza
              </p>
            </div>

            <div className="flex flex-col items-center space-y-3 p-6 rounded-lg hover:bg-white transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Shield className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold">Secure</h3>
              <p className="text-sm text-gray-600 text-center">
                Accesso protetto
              </p>
            </div>

            <div className="flex flex-col items-center space-y-3 p-6 rounded-lg hover:bg-white transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Zap className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold">Fast</h3>
              <p className="text-sm text-gray-600 text-center">
                Prestazioni ottimali
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-16 animate-in fade-in duration-1000 delay-700">
          <p className="text-sm text-gray-500">
            © 2024 Voilà Voice. Tutti i diritti riservati.
          </p>
        </div>
      </div>
    </div>
  );
}
