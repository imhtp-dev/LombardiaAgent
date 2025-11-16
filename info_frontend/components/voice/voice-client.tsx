"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Activity,
  Volume2,
  VolumeX,
  Loader2,
  AlertCircle,
  CheckCircle,
  Radio,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface VoiceClientProps {
  wsUrl?: string;
  sessionId?: string;
  startNode?: string;
  callerPhone?: string;
  onConnectionChange?: (connected: boolean) => void;
  onTranscriptUpdate?: (role: "user" | "assistant", text: string) => void;
}

interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

export function VoiceClient({
  wsUrl = "ws://localhost:8081/ws",
  sessionId,
  startNode = "greeting",
  callerPhone = "",
  onConnectionChange,
  onTranscriptUpdate,
}: VoiceClientProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
 
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioWorkletNodeRef = useRef<AudioWorkletNode | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);

  // Generate session ID if not provided
  const currentSessionId = sessionId || `web-${Date.now().toString(36)}`;

  // Cleanup function
  const cleanup = useCallback(() => {
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    audioWorkletNodeRef.current = null;
    audioQueueRef.current = [];
    isPlayingRef.current = false;

    setIsConnected(false);
    setIsConnecting(false);
    setIsAgentSpeaking(false);
    setIsUserSpeaking(false);

    onConnectionChange?.(false);
  }, [onConnectionChange]);

  // Convert Float32Array to Int16 PCM
  const float32ToInt16 = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16Array;
  };

  // Convert Int16 PCM to Float32Array
  const int16ToFloat32 = (int16Array: Int16Array): Float32Array => {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7fff);
    }
    return float32Array;
  };

  // Play audio from queue
  const playAudioQueue = useCallback(async () => {
    if (
      isPlayingRef.current ||
      audioQueueRef.current.length === 0 ||
      !audioContextRef.current ||
      isSpeakerMuted
    ) {
      return;
    }

    isPlayingRef.current = true;
    setIsAgentSpeaking(true);

    while (audioQueueRef.current.length > 0 && !isSpeakerMuted) {
      const audioData = audioQueueRef.current.shift();
      if (!audioData || !audioContextRef.current) break;

      const audioBuffer = audioContextRef.current.createBuffer(
        1,
        audioData.length,
        16000
      );
      audioBuffer.getChannelData(0).set(audioData);

      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      await new Promise<void>((resolve) => {
        source.onended = () => resolve();
        source.start();
      });
    }

    isPlayingRef.current = false;
    setIsAgentSpeaking(false);
  }, [isSpeakerMuted]);

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (isConnecting || isConnected) return;

    setIsConnecting(true);
    setConnectionError(null);

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });
      mediaStreamRef.current = stream;

      // Create audio context
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });

      // Build WebSocket URL with parameters
      const url = new URL(wsUrl);
      url.searchParams.set("session_id", currentSessionId);
      url.searchParams.set("start_node", startNode);
      if (callerPhone) {
        url.searchParams.set("caller_phone", callerPhone);
      }

      // Connect WebSocket
      const ws = new WebSocket(url.toString());
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        setIsConnecting(false);
        onConnectionChange?.(true);

        // Set up audio processing
        const source = audioContextRef.current!.createMediaStreamSource(stream);
        const processor = audioContextRef.current!.createScriptProcessor(
          4096,
          1,
          1
        );

        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN && !isMuted) {
            const inputData = e.inputBuffer.getChannelData(0);
            const int16Data = float32ToInt16(inputData);
            ws.send(int16Data.buffer);

            // Detect if user is speaking (simple volume detection)
            const volume = Math.sqrt(
              inputData.reduce((sum, val) => sum + val * val, 0) /
                inputData.length
            );
            setIsUserSpeaking(volume > 0.01);
          }
        };

        source.connect(processor);
        processor.connect(audioContextRef.current!.destination);
        audioWorkletNodeRef.current = processor as any;
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Received audio data from agent
          const int16Array = new Int16Array(event.data);
          const float32Array = int16ToFloat32(int16Array);
          audioQueueRef.current.push(float32Array);
          playAudioQueue();
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionError("Errore di connessione al voice agent");
        cleanup();
      };

      ws.onclose = () => {
        console.log("WebSocket closed");
        cleanup();
      };
    } catch (error) {
      console.error("Connection error:", error);
      setConnectionError(
        error instanceof Error
          ? error.message
          : "Impossibile accedere al microfono"
      );
      setIsConnecting(false);
      cleanup();
    }
  }, [
    isConnecting,
    isConnected,
    wsUrl,
    currentSessionId,
    startNode,
    callerPhone,
    isMuted,
    cleanup,
    onConnectionChange,
    playAudioQueue,
  ]);

  // Disconnect
  const disconnect = useCallback(() => {
    cleanup();
  }, [cleanup]);

  // Toggle mute
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => !prev);
  }, []);

  // Toggle speaker
  const toggleSpeaker = useCallback(() => {
    setIsSpeakerMuted((prev) => {
      const newValue = !prev;
      if (newValue) {
        // Clear audio queue when muting speaker
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        setIsAgentSpeaking(false);
      }
      return newValue;
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return (
    <div className="space-y-4">
      {/* Connection Error */}
      {connectionError && (
        <Alert variant="destructive" className="animate-in slide-in-from-top">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{connectionError}</AlertDescription>
        </Alert>
      )}

      {/* Voice Client Card */}
      <Card className="border-gray-100 shadow-lg">
        <CardContent className="pt-6">
          <div className="space-y-6">
            {/* Connection Status */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center transition-all",
                    isConnected
                      ? "bg-green-100 ring-4 ring-green-50"
                      : "bg-gray-100"
                  )}
                >
                  {isConnecting ? (
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  ) : isConnected ? (
                    <Activity className="h-6 w-6 text-green-600 animate-pulse" />
                  ) : (
                    <PhoneOff className="h-6 w-6 text-gray-400" />
                  )}
                </div>
                <div>
                  <h3 className="font-semibold">
                    {isConnected
                      ? "Connesso al Voice Agent"
                      : isConnecting
                      ? "Connessione in corso..."
                      : "Disconnesso"}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {isConnected
                      ? `Sessione: ${currentSessionId}`
                      : "Premi il pulsante per iniziare"}
                  </p>
                </div>
              </div>

              {/* Connection Badge */}
              <Badge
                variant={isConnected ? "default" : "outline"}
                className={cn(
                  "gap-2",
                  isConnected &&
                    "bg-green-600 hover:bg-green-700 border-green-600"
                )}
              >
                <span
                  className={cn(
                    "relative flex h-2 w-2",
                    isConnected && "animate-pulse"
                  )}
                >
                  <span
                    className={cn(
                      "absolute inline-flex h-full w-full rounded-full opacity-75",
                      isConnected ? "bg-white" : "bg-gray-400"
                    )}
                  ></span>
                  <span
                    className={cn(
                      "relative inline-flex rounded-full h-2 w-2",
                      isConnected ? "bg-white" : "bg-gray-400"
                    )}
                  ></span>
                </span>
                {isConnected ? "Online" : "Offline"}
              </Badge>
            </div>

            {/* Activity Indicators */}
            {isConnected && (
              <div className="grid grid-cols-2 gap-4">
                <div
                  className={cn(
                    "flex items-center gap-3 p-4 rounded-lg border-2 transition-all",
                    isUserSpeaking
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-100 bg-gray-50"
                  )}
                >
                  <Radio
                    className={cn(
                      "h-5 w-5",
                      isUserSpeaking
                        ? "text-blue-600 animate-pulse"
                        : "text-gray-400"
                    )}
                  />
                  <div>
                    <p className="text-sm font-medium">Il tuo microfono</p>
                    <p className="text-xs text-muted-foreground">
                      {isUserSpeaking ? "Parlando..." : "Silenzio"}
                    </p>
                  </div>
                </div>

                <div
                  className={cn(
                    "flex items-center gap-3 p-4 rounded-lg border-2 transition-all",
                    isAgentSpeaking
                      ? "border-green-500 bg-green-50"
                      : "border-gray-100 bg-gray-50"
                  )}
                >
                  <Volume2
                    className={cn(
                      "h-5 w-5",
                      isAgentSpeaking
                        ? "text-green-600 animate-pulse"
                        : "text-gray-400"
                    )}
                  />
                  <div>
                    <p className="text-sm font-medium">Voice Agent</p>
                    <p className="text-xs text-muted-foreground">
                      {isAgentSpeaking ? "Parlando..." : "In ascolto"}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Control Buttons */}
            <div className="flex gap-3">
              {!isConnected ? (
                <Button
                  onClick={connect}
                  disabled={isConnecting}
                  className="flex-1 h-14 text-base gap-3 bg-green-600 hover:bg-green-700"
                  size="lg"
                >
                  {isConnecting ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Connessione...
                    </>
                  ) : (
                    <>
                      <Phone className="h-5 w-5" />
                      Avvia Conversazione
                    </>
                  )}
                </Button>
              ) : (
                <>
                  <Button
                    onClick={disconnect}
                    variant="destructive"
                    className="flex-1 h-14 text-base gap-3"
                    size="lg"
                  >
                    <PhoneOff className="h-5 w-5" />
                    Termina Chiamata
                  </Button>

                  <Button
                    onClick={toggleMute}
                    variant={isMuted ? "destructive" : "outline"}
                    className="h-14 px-6"
                    size="lg"
                  >
                    {isMuted ? (
                      <MicOff className="h-5 w-5" />
                    ) : (
                      <Mic className="h-5 w-5" />
                    )}
                  </Button>

                  <Button
                    onClick={toggleSpeaker}
                    variant={isSpeakerMuted ? "destructive" : "outline"}
                    className="h-14 px-6"
                    size="lg"
                  >
                    {isSpeakerMuted ? (
                      <VolumeX className="h-5 w-5" />
                    ) : (
                      <Volume2 className="h-5 w-5" />
                    )}
                  </Button>
                </>
              )}
            </div>

            {/* Info Text */}
            {isConnected && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100">
                <CheckCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-900">
                  La conversazione vocale è attiva. Parla naturalmente con
                  l'agente virtuale Ualà.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
