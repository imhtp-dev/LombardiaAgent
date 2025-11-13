"use client";

import { useState, useEffect } from "react";
import { StatCard } from "@/components/dashboard/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Clock, 
  Euro, 
  Phone, 
  TrendingUp, 
  Search, 
  X, 
  ChevronLeft, 
  ChevronRight,
  FileText,
  Heart,
  Target,
  MessageCircle,
  Activity,
  BarChart3,
  PieChart as PieChartIcon,
  TrendingDown,
  CheckCircle,
  XCircle,
  AlertCircle,
  LucideIcon,
  Loader2
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import { dashboardApi, type DashboardStats, type Region, type CallListResponse, type CallItem } from "@/lib/api-client";

export default function DashboardPage() {
  const [selectedRegion, setSelectedRegion] = useState("All Region");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedCall, setSelectedCall] = useState<CallItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Real data state
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [calls, setCalls] = useState<CallListResponse | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [sentimentStats, setSentimentStats] = useState<Array<{ sentiment: string; count: number; color: string }>>([]);
  const [actionStats, setActionStats] = useState<Array<{ action: string; count: number; avg_duration?: number; color: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Load initial data
  useEffect(() => {
    loadRegions();
    loadDashboardData();
  }, []);

  // Reload when filters/page changes
  useEffect(() => {
    if (regions.length > 0) {
      loadDashboardData();
    }
  }, [selectedRegion, startDate, endDate, currentPage]);

  const loadRegions = async () => {
    try {
      const data = await dashboardApi.getRegions();
      setRegions(data);
    } catch (err) {
      console.error("Error loading regions:", err);
    }
  };

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError("");
    
    try {
      // Load stats
      const statsData = await dashboardApi.getStats({
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setStats(statsData);

      // Load calls
      const callsData = await dashboardApi.getCalls({
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setCalls(callsData);

      // Load additional stats
      const additionalStats = await dashboardApi.getAdditionalStats({
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      
      // Map sentiment stats with colors
      const sentimentColors: Record<string, string> = {
        positive: "#10b981",
        neutral: "#3b82f6",
        negative: "#ef4444",
      };
      setSentimentStats((additionalStats.sentiment_stats || []).map((s: { sentiment: string; count: number }) => ({
        ...s,
        color: sentimentColors[s.sentiment?.toLowerCase()] || "#6b7280"
      })));

      // Map action stats with colors
      const actionColors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];
      setActionStats((additionalStats.action_stats || []).map((a: { action: string; count: number; avg_duration?: number }, idx: number) => ({
        ...a,
        color: actionColors[idx % actionColors.length]
      })));

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore nel caricamento dei dati";
      setError(errorMessage);
      console.error("Error loading dashboard:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFilters = () => {
    setStartDate("");
    setEndDate("");
    setSelectedRegion("All Region");
    setCurrentPage(1);
  };

  const handleFilter = () => {
    setCurrentPage(1);
    loadDashboardData();
  };

  const handleViewCall = async (call: CallItem) => {
    setSelectedCall(call);
    setIsModalOpen(true);
  };

  const totalPages = calls?.pagination.total_pages || 1;
  const paginatedCalls = calls?.calls || [];
  const totalCalls = calls?.pagination.total_calls || 0;

  const getActionBadge = (action: string) => {
    const variants: Record<string, { variant: "default" | "destructive" | "outline" | "secondary"; label: string; icon: LucideIcon }> = {
      transfer: { variant: "secondary", label: "Transfer", icon: TrendingUp },
      book: { variant: "default", label: "Book", icon: CheckCircle },
      question: { variant: "outline", label: "Question", icon: MessageCircle },
      completed_by_voice_agent: { variant: "default", label: "Completed", icon: CheckCircle },
      time_limit: { variant: "destructive", label: "Time Limit", icon: Clock },
    };
    const config = variants[action] || { variant: "outline", label: action, icon: Activity };
    const Icon = config.icon;
    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getSentimentBadge = (sentiment: string) => {
    const variants: Record<string, { className: string; icon: LucideIcon }> = {
      positive: { className: "bg-green-100 text-green-800 hover:bg-green-200", icon: Heart },
      negative: { className: "bg-red-100 text-red-800 hover:bg-red-200", icon: TrendingDown },
      neutral: { className: "bg-blue-100 text-blue-800 hover:bg-blue-200", icon: Activity },
    };
    const config = variants[sentiment?.toLowerCase()] || { className: "", icon: Activity };
    const Icon = config.icon;
    return (
      <Badge className={`${config.className} gap-1`}>
        <Icon className="h-3 w-3" />
        {sentiment}
      </Badge>
    );
  };

  const getEsitoBadge = (esito: string) => {
    const variants: Record<string, { className: string; icon: LucideIcon }> = {
      COMPLETATA: { className: "bg-green-100 text-green-800 hover:bg-green-200", icon: CheckCircle },
      TRASFERITA: { className: "bg-yellow-100 text-yellow-800 hover:bg-yellow-200", icon: TrendingUp },
      "NON COMPLETATA": { className: "bg-red-100 text-red-800 hover:bg-red-200", icon: XCircle },
    };
    const config = variants[esito] || { className: "", icon: AlertCircle };
    const Icon = config.icon;
    return (
      <Badge className={`${config.className} gap-1`}>
        <Icon className="h-3 w-3" />
        {esito}
      </Badge>
    );
  };

  if (isLoading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Panoramica completa delle chiamate e statistiche
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Activity className="h-3 w-3" />
            Live
          </Badge>
        </div>
      </div>

      {/* Filters */}
      <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium">Regione</Label>
              <Select value={selectedRegion} onValueChange={setSelectedRegion}>
                <SelectTrigger className="border-gray-200 hover:border-blue-300 transition-colors">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {regions.map((region) => (
                    <SelectItem key={region.value} value={region.value}>
                      {region.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Data Inizio</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="border-gray-200 hover:border-blue-300 transition-colors"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Data Fine</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="border-gray-200 hover:border-blue-300 transition-colors"
              />
            </div>
            <div className="space-y-2 sm:col-span-2 lg:col-span-1 xl:col-span-2">
              <Label className="invisible text-sm">Actions</Label>
              <div className="flex gap-2">
                <Button onClick={handleFilter} variant="default" className="flex-1 gap-2 hover:scale-105 transition-transform">
                  <Search className="h-4 w-4" />
                  <span className="hidden sm:inline">Filtra</span>
                </Button>
                <Button variant="outline" onClick={handleClearFilters} className="flex-1 gap-2 hover:scale-105 transition-transform">
                  <X className="h-4 w-4" />
                  <span className="hidden sm:inline">Reset</span>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Totale Minuti"
          value={isLoading ? "..." : `${(stats?.total_minutes || 0).toLocaleString()} min`}
          icon={Clock}
          iconColor="text-blue-600"
        />
        <StatCard
          title="Corrispettivo Euro"
          value={isLoading ? "..." : `€ ${(stats?.total_revenue || 0).toFixed(2)}`}
          icon={Euro}
          iconColor="text-green-600"
        />
        <StatCard
          title="Nr. Chiamate"
          value={isLoading ? "..." : (stats?.total_calls || 0).toLocaleString()}
          icon={Phone}
          iconColor="text-purple-600"
        />
        <StatCard
          title="Durata Media"
          value={isLoading ? "..." : `${(stats?.avg_duration_minutes || 0).toFixed(1)} min`}
          icon={TrendingUp}
          iconColor="text-yellow-600"
        />
      </div>

      {/* Charts Row */}
      {sentimentStats.length > 0 || actionStats.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sentimentStats.length > 0 && (
            <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Heart className="h-5 w-5 text-blue-600" />
                  Distribuzione Sentiment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={sentimentStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => entry.sentiment}
                      outerRadius={70}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {sentimentStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {actionStats.length > 0 && (
            <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="h-5 w-5 text-blue-600" />
                  Distribuzione Azioni
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={actionStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => entry.action}
                      outerRadius={70}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {actionStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      ) : null}

      {/* Recent Calls Table */}
      <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5 text-blue-600" />
              Chiamate Recenti
            </CardTitle>
            <Badge variant="secondary" className="gap-1">
              <Activity className="h-3 w-3" />
              {totalCalls} chiamate
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : (
            <>
              <div className="rounded-lg border border-gray-100 overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50/50 hover:bg-gray-50/50">
                      <TableHead className="font-semibold">ID</TableHead>
                      <TableHead className="font-semibold">Data/Ora</TableHead>
                      <TableHead className="font-semibold">Telefono</TableHead>
                      <TableHead className="font-semibold">Durata</TableHead>
                      <TableHead className="font-semibold">Azione</TableHead>
                      <TableHead className="font-semibold">Sentiment</TableHead>
                      <TableHead className="font-semibold">Esito</TableHead>
                      <TableHead className="font-semibold">Motivazione</TableHead>
                      <TableHead className="font-semibold">Azioni</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedCalls.length > 0 ? (
                      paginatedCalls.map((call) => (
                        <TableRow key={call.id} className="hover:bg-blue-50/50 transition-colors">
                          <TableCell className="font-medium">{call.id}</TableCell>
                          <TableCell className="text-sm">
                            {call.started_at ? new Date(call.started_at).toLocaleString("it-IT") : "N/A"}
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {call.phone_number || "N/A"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="gap-1">
                              <Clock className="h-3 w-3" />
                              {call.duration_seconds}s
                            </Badge>
                          </TableCell>
                          <TableCell>{getActionBadge(call.action)}</TableCell>
                          <TableCell>{getSentimentBadge(call.sentiment)}</TableCell>
                          <TableCell>{getEsitoBadge(call.esito_chiamata || "N/A")}</TableCell>
                          <TableCell className="text-sm">{call.motivazione || "N/A"}</TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewCall(call)}
                              className="gap-1 hover:bg-blue-50 hover:text-blue-700 transition-all"
                            >
                              <FileText className="h-4 w-4" />
                              Dettagli
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                          Nessuna chiamata trovata per i filtri selezionati
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalCalls > 0 && (
                <div className="flex flex-col sm:flex-row items-center justify-between mt-4 gap-4">
                  <div className="text-sm text-muted-foreground">
                    Mostrando {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, totalCalls)} di{" "}
                    {totalCalls} chiamate
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="gap-1 hover:scale-105 transition-transform"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Precedente
                    </Button>
                    <div className="text-sm font-medium px-3">
                      Pagina {currentPage} di {totalPages}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="gap-1 hover:scale-105 transition-transform"
                    >
                      Successiva
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Call Details Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto border-gray-100">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Dettagli Chiamata
            </DialogTitle>
          </DialogHeader>
          {selectedCall && (
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="summary" className="gap-2">
                  <FileText className="h-4 w-4" />
                  Summary
                </TabsTrigger>
                <TabsTrigger value="intent" className="gap-2">
                  <Target className="h-4 w-4" />
                  Patient Intent
                </TabsTrigger>
                <TabsTrigger value="transcript" className="gap-2">
                  <MessageCircle className="h-4 w-4" />
                  Transcript
                </TabsTrigger>
              </TabsList>
              <TabsContent value="summary" className="space-y-4 mt-4">
                <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Call ID:</strong>
                    <code className="text-sm bg-white px-2 py-1 rounded">{selectedCall.call_id || "N/A"}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Durata:</strong>
                    <span className="text-sm">{selectedCall.duration_seconds}s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Telefono:</strong>
                    <span className="text-sm font-mono">{selectedCall.phone_number || "N/A"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Azione:</strong>
                    {getActionBadge(selectedCall.action)}
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Sentiment:</strong>
                    {getSentimentBadge(selectedCall.sentiment)}
                  </div>
                </div>
              </TabsContent>
              <TabsContent value="intent" className="space-y-4 mt-4">
                <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Esito:</strong>
                    {getEsitoBadge(selectedCall.esito_chiamata || "N/A")}
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Motivazione:</strong>
                    <span className="text-sm">{selectedCall.motivazione || "N/A"}</span>
                  </div>
                </div>
              </TabsContent>
              <TabsContent value="transcript" className="space-y-4 mt-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-muted-foreground font-mono">
                    Transcript completo disponibile per chiamate con registrazione.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
