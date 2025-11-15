"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Mic, CheckCircle, AlertCircle, Activity, Phone, Clock, TrendingUp, Zap, Shield, Loader2 } from "lucide-react";
import { dashboardApi, type VoiceAgent } from "@/lib/api-client";

export default function VoiceAgentPage() {
  const [alert, setAlert] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [voiceAgents, setVoiceAgents] = useState<VoiceAgent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load voice agents on mount
  useEffect(() => {
    loadVoiceAgents();
  }, []);

  const loadVoiceAgents = async () => {
    setIsLoading(true);
    try {
      const data = await dashboardApi.getVoiceAgents();
      setVoiceAgents(data);
    } catch (err) {
      console.error("Error loading voice agents:", err);
      showAlert("Errore nel caricamento dei voice agent", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const showAlert = (message: string, type: "success" | "error" | "info") => {
    setAlert({ message, type });
    setTimeout(() => setAlert(null), 5000);
  };

  const handleToggle = (agent: VoiceAgent, currentState: boolean) => {
    const newState = !currentState;
    const action = newState ? "attivato" : "disattivato";
    
    // Note: In a real implementation, you would call an API to update the agent status
    // For now, we just show a message
    showAlert(`Voice Agent ${agent.regione} ${action} (nota: funzionalità di toggle da implementare nel backend)`, "info");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
          Voilà Voice Agent
        </h1>
        <p className="text-base text-gray-600">
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
                {voiceAgents.length} voice agent configurati
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
      {voiceAgents.length === 0 ? (
        <Card className="border-dashed border-gray-200">
          <CardContent className="pt-6 text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <Mic className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Nessun voice agent configurato</h3>
            <p className="text-muted-foreground text-sm">
              Configura i voice agent nella tabella tb_voice_agent
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {voiceAgents.map((agent) => (
            <Card key={agent.id_voice_agent} className="border-gray-100 shadow-sm hover:shadow-lg transition-all hover:-translate-y-1">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <Mic className="h-5 w-5 text-blue-600" />
                      {agent.regione}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-1 font-mono">
                      ID: {agent.assistant_id}
                    </p>
                  </div>
                  <Badge variant="default" className="gap-1 bg-green-100 text-green-800">
                    <Activity className="h-3 w-3" />
                    Attivo
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Statistics Placeholder */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 rounded-lg bg-white border border-gray-100 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-muted-foreground">Assistant ID</span>
                    </div>
                    <span className="font-mono text-xs">{agent.assistant_id.substring(0, 8)}...</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded-lg bg-white border border-gray-100 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-muted-foreground">Region</span>
                    </div>
                    <span className="font-semibold">{agent.regione}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded-lg bg-white border border-gray-100 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      <span className="text-sm text-muted-foreground">Status</span>
                    </div>
                    <Badge className="bg-green-100 text-green-800">Active</Badge>
                  </div>
                </div>

                {/* Toggle Switch - Note: Backend API for toggle not yet implemented */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-gray-50 to-white border border-gray-100">
                  <Label htmlFor={`toggle-${agent.id_voice_agent}`} className="cursor-pointer font-medium flex items-center gap-2">
                    <Zap className="h-4 w-4" />
                    Gestisci Agent
                  </Label>
                  <Switch
                    id={`toggle-${agent.id_voice_agent}`}
                    checked={true}
                    onCheckedChange={() => handleToggle(agent, true)}
                    className="data-[state=checked]:bg-blue-600"
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

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
                I voice agent sono gestiti tramite Pipecat e sono sempre attivi quando il server è in esecuzione
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <Activity className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                Le statistiche delle chiamate sono visibili nella Dashboard principale con filtro per regione
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
              <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                Assicurati che la base di conoscenza (Q&A) sia aggiornata per ogni regione attiva
              </span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
