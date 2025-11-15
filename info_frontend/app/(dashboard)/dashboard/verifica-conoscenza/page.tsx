"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Send, MessageSquare, Bot, User, Loader2, Trash2, Sparkles, Database, Network } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  functionCalled?: "RAG" | "GRAPH" | null;
}

export default function VerificaConoscenzaPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [charCount, setCharCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const currentAssistantMessageRef = useRef<string>("");
  const maxChars = 1000;

  // Check API connection on mount
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:8081/health');
        if (response.ok) {
          setIsConnected(true);
        }
      } catch (error) {
        setIsConnected(false);
      }
    };
    
    checkConnection();
    const interval = setInterval(checkConnection, 10000);
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading || inputMessage.length > maxChars || !isConnected) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageToSend = inputMessage;
    setInputMessage("");
    setCharCount(0);

    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch('http://localhost:8081/api/chat/send', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageToSend,
          region: 'Piemonte'
        })
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(data.timestamp),
        functionCalled: data.function_called,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Mi dispiace, si è verificato un errore. Per favore riprova.",
        timestamp: new Date(),
        functionCalled: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleClearChat = () => {
    if (confirm("Sei sicuro di voler cancellare la conversazione?")) {
      setMessages([]);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header with Stats */}
      <div className="flex-shrink-0 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              Verifica Conoscenza
            </h1>
            <p className="text-base text-gray-600">
              Testa la conoscenza del voice agent in tempo reale
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className={cn(
                "absolute inset-0 rounded-full blur-md opacity-20 animate-pulse",
                isConnected ? "bg-green-500" : "bg-red-500"
              )}></div>
              <Badge 
                variant="outline"
                className={cn(
                  "relative gap-2 px-4 py-1.5 backdrop-blur-sm",
                  isConnected 
                    ? "border-green-200 bg-green-50/50 text-green-700" 
                    : "border-red-200 bg-red-50/50 text-red-700"
                )}
              >
                <span className="relative flex h-2 w-2">
                  {isConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                  <span className={cn(
                    "relative inline-flex rounded-full h-2 w-2",
                    isConnected ? "bg-green-500" : "bg-red-500"
                  )}></span>
                </span>
                {isConnected ? "Connesso" : "Disconnesso"}
              </Badge>
            </div>
            <Button 
              variant="outline" 
              onClick={handleClearChat} 
              className="gap-2 border-2 hover:bg-gray-50 hover:border-gray-300 transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 font-medium h-10"
            >
              <Trash2 className="h-4 w-4" />
              Cancella Chat
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Messaggi</p>
                  <p className="text-2xl font-bold">{messages.length}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                  <MessageSquare className="h-5 w-5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">RAG Calls</p>
                  <p className="text-2xl font-bold">
                    {messages.filter((m) => m.functionCalled === "RAG").length}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                  <Database className="h-5 w-5 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Graph Calls</p>
                  <p className="text-2xl font-bold">
                    {messages.filter((m) => m.functionCalled === "GRAPH").length}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                  <Network className="h-5 w-5 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Chat Interface */}
      <Card className="flex flex-col border-gray-100 shadow-md overflow-hidden" style={{ height: '600px' }}>
        <CardHeader className="border-b bg-gradient-to-r from-blue-50/50 to-white flex-shrink-0 py-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            Conversazione con Voice Agent
          </CardTitle>
        </CardHeader>
        
        <div className="flex-1 overflow-y-auto p-4 bg-gray-50/30" style={{ minHeight: 0 }}>
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-sm">
                <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-100 to-blue-50 flex items-center justify-center">
                  <Bot className="h-10 w-10 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Inizia una conversazione</h3>
                <p className="text-sm text-muted-foreground">
                  Fai una domanda per testare la conoscenza del voice agent
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  } animate-in slide-in-from-bottom duration-300`}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div className="flex flex-col max-w-[75%]">
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.role === "user"
                          ? "bg-blue-600 text-white shadow-sm"
                          : "bg-white text-gray-900 shadow-sm border border-gray-100"
                      }`}
                    >
                      <p className="text-sm leading-relaxed break-words whitespace-pre-wrap">{message.content}</p>
                    </div>
                    <div className="flex items-center gap-2 mt-1 px-2">
                      <p className="text-xs text-muted-foreground">
                        {message.timestamp.toLocaleTimeString("it-IT", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                      {message.functionCalled && (
                        <Badge
                          variant="outline"
                          className={`text-xs gap-1 ${
                            message.functionCalled === "RAG"
                              ? "bg-purple-50 text-purple-700 border-purple-200"
                              : "bg-green-50 text-green-700 border-green-200"
                          }`}
                        >
                          {message.functionCalled === "RAG" ? (
                            <Database className="h-3 w-3" />
                          ) : (
                            <Network className="h-3 w-3" />
                          )}
                          {message.functionCalled}
                        </Badge>
                      )}
                    </div>
                  </div>
                  {message.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center flex-shrink-0 shadow-sm">
                      <User className="h-5 w-5 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
                <div className="flex gap-3 justify-start animate-in slide-in-from-bottom duration-300">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-100">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
        
        {/* Input Area */}
        <div className="border-t bg-white p-4 flex-shrink-0">
          <form onSubmit={handleSendMessage} className="space-y-2">
            <div className="flex gap-3">
              <Input
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => {
                  setInputMessage(e.target.value);
                  setCharCount(e.target.value.length);
                }}
                placeholder={isConnected ? "Scrivi un messaggio..." : "Connessione in corso..."}
                disabled={isLoading || !isConnected}
                maxLength={maxChars}
                className="flex-1 border-gray-200 hover:border-blue-300 focus:border-blue-500 transition-colors h-11"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
              />
              <Button 
                type="submit" 
                disabled={isLoading || !inputMessage.trim() || !isConnected}
                className="gap-2 px-6 h-11 hover:scale-105 transition-transform"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {!isLoading && <Send className="h-4 w-4" />}
                <span>{isLoading ? "Invio..." : "Invia"}</span>
              </Button>
            </div>
            <div className="flex items-center justify-between px-1">
              <p className="text-xs text-muted-foreground">
                Premi Invio per inviare • Shift+Invio per andare a capo
              </p>
              <p className={`text-xs font-medium ${
                charCount > 800 ? "text-red-600" :
                charCount > 600 ? "text-yellow-600" :
                "text-muted-foreground"
              }`}>
                {charCount}/{maxChars}
              </p>
            </div>
          </form>
        </div>
      </Card>

      {/* Instructions */}
      <Card className="border-gray-100 shadow-sm flex-shrink-0">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            Come Utilizzare
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-3 gap-3 text-sm">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
              <MessageSquare className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <span className="text-muted-foreground">
                Fai domande per testare la conoscenza del voice agent con memoria conversazionale
              </span>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors">
              <Database className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <span className="text-muted-foreground">
                Badge <strong className="text-purple-700">RAG</strong> indica query su database
              </span>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-green-50 hover:bg-green-100 transition-colors">
              <Network className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-muted-foreground">
                Badge <strong className="text-green-700">GRAPH</strong> indica chiamata API
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
