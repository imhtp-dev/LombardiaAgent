"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mic, CheckCircle, AlertCircle, Activity, Phone, Clock, TrendingUp, Zap, Shield } from "lucide-react";

export default function VoiceAgentPage() {
  const [piemonteEnabled, setPiemonteEnabled] = useState(true);
  const [lombardiaEnabled, setLombardiaEnabled] = useState(false);
  const [venetoEnabled, setVenetoEnabled] = useState(false);
  const [alert, setAlert] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const showAlert = (message: string, type: "success" | "error" | "info") => {
    setAlert({ message, type });
    setTimeout(() => setAlert(null), 5000);
  };

  const handleToggle = (region: string, currentState: boolean) => {
    const newState = !currentState;
    const action = newState ? "attivato" : "disattivato";
    
    switch (region) {
      case "Piemonte":
        setPiemonteEnabled(newState);
        break;
      case "Lombardia":
        setLombardiaEnabled(newState);
        break;
      case "Veneto":
        setVenetoEnabled(newState);
        break;
    }
    
    showAlert(`Voice Agent ${region} ${action} con successo`, "success");
  };

  const regions = [
    {
      name: "Piemonte",
      enabled: piemonteEnabled,
      setEnabled: () => handleToggle("Piemonte", piemonteEnabled),
      stats: {
        callsToday: 245,
        avgDuration: "3.2 min",
        successRate: "87%",
      },
    },
    {
      name: "Lombardia",
      enabled: lombardiaEnabled,
      setEnabled: () => handleToggle("Lombardia", lombardiaEnabled),
      stats: {
        callsToday: 0,
        avgDuration: "0 min",
        successRate: "0%",
      },
    },
    {
      name: "Veneto",
      enabled: venetoEnabled,
      setEnabled: () => handleToggle("Veneto", venetoEnabled),
      stats: {
        callsToday: 0,
        avgDuration: "0 min",
        successRate: "0%",
      },
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Voilà Voice Agent</h1>
        <p className="text-muted-foreground mt-1">
          Controlla e gestisci i voice agent per regione
        </p>
      </div>

      {/* Alert */}
      {alert && (
        <Alert
          variant={alert.type === "error" ? "destructive" : "default"}
          className={`${
            alert.type === "success"
              ? "border-green-200 bg-green-50 text-green-800"
              : alert.type === "info"
              ? "border-blue-200 bg-blue-50 text-blue-800"
              : ""
          } animate-in slide-in-from-top duration-300`}
        >
          {alert.type === "success" && <CheckCircle className="h-4 w-4" />}
          {alert.type === "error" && <AlertCircle className="h-4 w-4" />}
          {alert.type === "info" && <AlertCircle className="h-4 w-4" />}
          <AlertDescription>{alert.message}</AlertDescription>
        </Alert>
      )}

      {/* System Status */}
      <Card className="border-blue-100 bg-gradient-to-r from-blue-50 to-blue-50/30 shadow-sm">
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center ring-4 ring-blue-50">
              <Zap className="h-7 w-7 text-blue-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg">Stato Sistema</h3>
              <p className="text-sm text-muted-foreground">
                {regions.filter((r) => r.enabled).length} di {regions.length} voice agent attivi
              </p>
            </div>
            <Badge variant="default" className="bg-green-600 gap-1 px-3 py-1">
              <Activity className="h-3 w-3" />
              Online
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Voice Agent Controls */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {regions.map((region) => (
          <Card key={region.name} className={`${
            region.enabled 
              ? "border-blue-200 bg-gradient-to-br from-blue-50/50 to-white" 
              : "border-gray-100"
          } shadow-sm hover:shadow-lg transition-all hover:-translate-y-1`}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    <Mic className={`h-5 w-5 ${region.enabled ? "text-blue-600" : "text-gray-400"}`} />
                    {region.name}
                  </CardTitle>
                </div>
                <Badge
                  variant={region.enabled ? "default" : "secondary"}
                  className={`gap-1 ${
                    region.enabled
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  <Activity className="h-3 w-3" />
                  {region.enabled ? "Attivo" : "Inattivo"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Statistics */}
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 rounded-lg bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-muted-foreground">Chiamate Oggi</span>
                  </div>
                  <span className="font-semibold">{region.stats.callsToday}</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-muted-foreground">Durata Media</span>
                  </div>
                  <span className="font-semibold">{region.stats.avgDuration}</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-600" />
                    <span className="text-sm text-muted-foreground">Tasso Successo</span>
                  </div>
                  <span className="font-semibold">{region.stats.successRate}</span>
                </div>
              </div>

              {/* Toggle Switch */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-gray-50 to-white border border-gray-100">
                <Label htmlFor={`toggle-${region.name}`} className="cursor-pointer font-medium flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  {region.enabled ? "Disattiva" : "Attiva"} Voice Agent
                </Label>
                <Switch
                  id={`toggle-${region.name}`}
                  checked={region.enabled}
                  onCheckedChange={region.setEnabled}
                  className="data-[state=checked]:bg-blue-600"
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Configuration Note */}
      <Card className="border-gray-100 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            Note di Configurazione
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <CheckCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                L'attivazione o disattivazione di un voice agent ha effetto immediato sul sistema
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <Activity className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                Le statistiche vengono aggiornate in tempo reale e resettate ogni mezzanotte
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                Assicurati che la base di conoscenza sia aggiornata prima di attivare un voice agent
              </span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
