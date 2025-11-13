"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle } from "lucide-react";
import { authApi } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Call real API
      const result = await authApi.login({
        email,
        password,
        remember_me: rememberMe,
      });

      if (result.success) {
        // Token is already stored in localStorage by authApi.login
        router.push("/dashboard");
      } else {
        setError(result.message || "Errore durante il login");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore durante il login. Riprova.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-8">
          {/* Logo */}
          <div className="flex flex-col items-center space-y-6">
            <div className="relative w-20 h-20">
              <Image
                src="/images/Voila_matita.png"
                alt="Voilà Voice"
                fill
                className="object-contain"
                priority
              />
            </div>
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-semibold text-gray-900">
                Accedi a Voilà Voice
              </h1>
              <p className="text-sm text-gray-600">
                Inserisci le tue credenziali per continuare
              </p>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <Alert variant="destructive" className="border-red-200 bg-red-50">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-800">{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="nome@esempio.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Inserisci la password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remember"
                  checked={rememberMe}
                  onCheckedChange={(checked) => setRememberMe(checked as boolean)}
                  disabled={isLoading}
                  className="border-gray-300"
                />
                <Label
                  htmlFor="remember"
                  className="text-sm text-gray-700 cursor-pointer font-normal"
                >
                  Ricordami
                </Label>
              </div>
              <Button
                type="button"
                variant="link"
                className="px-0 text-sm text-blue-600 hover:text-blue-700 font-medium"
                disabled={isLoading}
              >
                Password dimenticata?
              </Button>
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Accesso in corso...
                </>
              ) : (
                "Accedi"
              )}
            </Button>

            <div className="text-center">
              <p className="text-xs text-gray-500">
                Demo: <span className="font-medium text-gray-700">demo@voila.com</span> / 
                <span className="font-medium text-gray-700"> demo</span>
              </p>
            </div>
          </form>
        </div>
      </div>

      {/* Right side - Brand/Image */}
      <div className="hidden lg:flex lg:flex-1 bg-gradient-to-br from-blue-600 to-blue-800 items-center justify-center p-12">
        <div className="max-w-md space-y-6 text-white">
          <h2 className="text-4xl font-bold leading-tight">
            Gestisci le tue chiamate con intelligenza
          </h2>
          <p className="text-lg text-blue-100">
            Dashboard completa per monitorare e analizzare tutte le chiamate del tuo voice agent in tempo reale.
          </p>
          <div className="space-y-3 pt-4">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-white"></div>
              <span className="text-blue-50">Statistiche in tempo reale</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-white"></div>
              <span className="text-blue-50">Analisi sentiment e KPI</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-white"></div>
              <span className="text-blue-50">Gestione conoscenza AI</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
