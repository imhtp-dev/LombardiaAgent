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
import { dashboardApi, type DashboardStats, type Region, type CallListResponse, type CallItem, type TrendDataPoint, type CallOutcomeStats } from "@/lib/api-client";
import { Skeleton } from "@/components/ui/skeleton";

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

  // New state for additional charts
  const [outcomeTrendData, setOutcomeTrendData] = useState<Array<{ date: string; COMPLETATA: number; TRASFERITA: number; "NON COMPLETATA": number }>>([]);
  const [sentimentTrendData, setSentimentTrendData] = useState<Array<{ date: string; positive: number; neutral: number; negative: number }>>([]);
  const [motivazioneStats, setMotivazioneStats] = useState<Array<{ motivazione: string; count: number; color: string }>>([]);
  const [esitoStats, setEsitoStats] = useState<Array<{ esito: string; count: number; color: string }>>([]);

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

      // Load outcome trend data
      const outcomeTrendResponse = await dashboardApi.getCallOutcomeTrend({
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      // Transform outcome trend data for line chart
      const outcomeByDate: Record<string, { COMPLETATA: number; TRASFERITA: number; "NON COMPLETATA": number }> = {};
      outcomeTrendResponse.data.forEach((item: any) => {
        if (!outcomeByDate[item.date]) {
          outcomeByDate[item.date] = { COMPLETATA: 0, TRASFERITA: 0, "NON COMPLETATA": 0 };
        }
        if (item.esito_chiamata) {
          outcomeByDate[item.date][item.esito_chiamata as keyof typeof outcomeByDate[typeof item.date]] = item.count;
        }
      });
      setOutcomeTrendData(Object.keys(outcomeByDate).sort().map(date => ({ date, ...outcomeByDate[date] })));

      // Load sentiment trend data
      const sentimentTrendResponse = await dashboardApi.getSentimentTrend({
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      // Transform sentiment trend data for line chart
      const sentimentByDate: Record<string, { positive: number; neutral: number; negative: number }> = {};
      sentimentTrendResponse.data.forEach((item: any) => {
        if (!sentimentByDate[item.date]) {
          sentimentByDate[item.date] = { positive: 0, neutral: 0, negative: 0 };
        }
        if (item.sentiment) {
          sentimentByDate[item.date][item.sentiment as keyof typeof sentimentByDate[typeof item.date]] = item.count;
        }
      });
      setSentimentTrendData(Object.keys(sentimentByDate).sort().map(date => ({ date, ...sentimentByDate[date] })));

      // Load call outcome stats for motivazione and esito pie charts
      const outcomeStats = await dashboardApi.getCallOutcomeStats({
        region: selectedRegion,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });

      // Map motivazione stats with colors (using correct field name: motivation_stats)
      const motivazioneColors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
      setMotivazioneStats((outcomeStats.motivation_stats || []).map((m: { motivazione: string; count: number }, idx: number) => ({
        motivazione: m.motivazione,
        count: m.count,
        color: motivazioneColors[idx % motivazioneColors.length]
      })));

      // Map esito stats with specific colors (using correct field name: outcome_stats)
      const esitoColors: Record<string, string> = {
        "COMPLETATA": "#10b981",
        "TRASFERITA": "#f59e0b",
        "NON COMPLETATA": "#ef4444"
      };
      setEsitoStats((outcomeStats.outcome_stats || []).map((e: { esito_chiamata: string; count: number }) => ({
        esito: e.esito_chiamata,
        count: e.count,
        color: esitoColors[e.esito_chiamata] || "#6b7280"
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
    try {
      // Fetch full call details including summary and transcript from backend
      const callDetails = await dashboardApi.getCallSummary(call.call_id || "");
      setSelectedCall({ ...call, ...callDetails });
      setIsModalOpen(true);
    } catch (error) {
      console.error("Error fetching call details:", error);
      // Fallback to basic data if API call fails
      setSelectedCall(call);
      setIsModalOpen(true);
    }
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

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="text-base text-gray-600">
            Panoramica completa delle chiamate e statistiche
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-green-500 rounded-full blur-md opacity-20 animate-pulse"></div>
            <Badge variant="outline" className="relative gap-2 px-4 py-1.5 border-green-200 bg-green-50/50 text-green-700 backdrop-blur-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Live
            </Badge>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300 backdrop-blur-sm bg-white/80">
        <CardContent className="pt-6 pb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-5">
            <div className="space-y-2.5">
              <Label className="text-sm font-semibold text-gray-700">Regione</Label>
              <Select value={selectedRegion} onValueChange={setSelectedRegion}>
                <SelectTrigger className="h-11 border-gray-200 hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all duration-200 bg-white">
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
            <div className="space-y-2.5">
              <Label className="text-sm font-semibold text-gray-700">Data Inizio</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-11 border-gray-200 hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all duration-200"
              />
            </div>
            <div className="space-y-2.5">
              <Label className="text-sm font-semibold text-gray-700">Data Fine</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-11 border-gray-200 hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all duration-200"
              />
            </div>
            <div className="space-y-2.5 sm:col-span-2 lg:col-span-1 xl:col-span-2">
              <Label className="invisible text-sm">Actions</Label>
              <div className="flex gap-3">
                <Button 
                  onClick={handleFilter} 
                  className="flex-1 h-11 gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white shadow-md hover:shadow-lg transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 font-medium"
                >
                  <Search className="h-4 w-4 text-white" />
                  <span className="hidden sm:inline">Filtra</span>
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleClearFilters} 
                  className="flex-1 h-11 gap-2 border-2 hover:bg-gray-50 hover:border-gray-300 transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 font-medium"
                >
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
        {isLoading && !stats ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="border border-gray-200/60">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-3 flex-1">
                      <Skeleton className="h-3 w-24" />
                      <Skeleton className="h-8 w-32" />
                    </div>
                    <Skeleton className="h-16 w-16 rounded-2xl" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        ) : (
          <>
            <StatCard
              title="Totale Minuti"
              value={`${(stats?.total_minutes || 0).toLocaleString()} min`}
              icon={Clock}
              iconColor="text-blue-600"
            />
            <StatCard
              title="Corrispettivo Euro"
              value={`€ ${(stats?.total_revenue || 0).toFixed(2)}`}
              icon={Euro}
              iconColor="text-green-600"
            />
            <StatCard
              title="Nr. Chiamate"
              value={(stats?.total_calls || 0).toLocaleString()}
              icon={Phone}
              iconColor="text-purple-600"
            />
            <StatCard
              title="Durata Media"
              value={`${(stats?.avg_duration_minutes || 0).toFixed(1)} min`}
              icon={TrendingUp}
              iconColor="text-yellow-600"
            />
          </>
        )}
      </div>

      {/* Line Charts Row - Trends Over Time */}
      {(outcomeTrendData.length > 0 || sentimentTrendData.length > 0) && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Esito Chiamata Trend */}
          {outcomeTrendData.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100">
                    <BarChart3 className="h-5 w-5 text-blue-600" />
                  </div>
                  Andamento Esito Chiamate
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={outcomeTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      wrapperStyle={{ paddingTop: '20px' }}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700">{value}</span>}
                    />
                    <Line
                      type="monotone"
                      dataKey="COMPLETATA"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ fill: '#10b981', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="TRASFERITA"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={{ fill: '#f59e0b', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="NON COMPLETATA"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={{ fill: '#ef4444', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Sentiment Trend */}
          {sentimentTrendData.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-purple-50 to-purple-100">
                    <TrendingUp className="h-5 w-5 text-purple-600" />
                  </div>
                  Andamento Sentiment
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={sentimentTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      wrapperStyle={{ paddingTop: '20px' }}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700 capitalize">{value}</span>}
                    />
                    <Line
                      type="monotone"
                      dataKey="positive"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ fill: '#10b981', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="neutral"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ fill: '#3b82f6', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="negative"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={{ fill: '#ef4444', r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Pie Charts Row */}
      {sentimentStats.length > 0 || actionStats.length > 0 || motivazioneStats.length > 0 || esitoStats.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {sentimentStats.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-pink-50 to-pink-100">
                    <Heart className="h-5 w-5 text-pink-600" />
                  </div>
                  Distribuzione Sentiment
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={sentimentStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={false}
                      outerRadius={85}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="sentiment"
                      strokeWidth={2}
                      stroke="#fff"
                    >
                      {sentimentStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700 capitalize">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="text-center mt-4 pt-4 border-t border-gray-100">
                  <p className="text-sm font-semibold text-gray-600">
                    {sentimentStats.reduce((sum, item) => sum + item.count, 0)} chiamate totali
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Distribuzione Azioni Chart - Commented out */}
          {/* {actionStats.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100">
                    <Target className="h-5 w-5 text-blue-600" />
                  </div>
                  Distribuzione Azioni
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={actionStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={false}
                      outerRadius={85}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="action"
                      strokeWidth={2}
                      stroke="#fff"
                    >
                      {actionStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700 capitalize">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )} */}

          {/* Motivazione Distribution */}
          {motivazioneStats.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-amber-50 to-amber-100">
                    <MessageCircle className="h-5 w-5 text-amber-600" />
                  </div>
                  Distribuzione Motivazioni
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={motivazioneStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={false}
                      outerRadius={85}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="motivazione"
                      strokeWidth={2}
                      stroke="#fff"
                    >
                      {motivazioneStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Esito Chiamata Distribution */}
          {esitoStats.length > 0 && (
            <Card className="border border-gray-200/60 shadow-sm hover:shadow-lg transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-green-50 to-green-100">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  </div>
                  Distribuzione Esito Chiamate
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-6">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={esitoStats}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={false}
                      outerRadius={85}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="esito"
                      strokeWidth={2}
                      stroke="#fff"
                    >
                      {esitoStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value) => <span className="text-sm font-medium text-gray-700">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="text-center mt-4 pt-4 border-t border-gray-100">
                  <p className="text-sm font-semibold text-gray-600">
                    {esitoStats.reduce((sum, item) => sum + item.count, 0)} chiamate totali
                  </p>
                </div>
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
                {isLoading ? (
                  <>
                    {[...Array(5)].map((_, i) => (
                      <TableRow key={i} className="border-b">
                        <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-16 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-20 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-20 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-24 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-20 rounded-lg" /></TableCell>
                      </TableRow>
                    ))}
                  </>
                ) : paginatedCalls.length > 0 ? (
                      paginatedCalls.map((call, index) => (
                        <TableRow 
                          key={call.id} 
                          className="group hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-transparent border-b transition-all duration-200"
                          style={{ animationDelay: `${index * 50}ms` }}
                        >
                          <TableCell className="font-semibold text-gray-900">{call.id}</TableCell>
                          <TableCell className="text-sm text-gray-600">
                            {call.started_at ? new Date(call.started_at).toLocaleString("it-IT") : "N/A"}
                          </TableCell>
                          <TableCell className="font-mono text-sm text-gray-700">
                            {call.phone_number || "N/A"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="gap-1 font-medium">
                              <Clock className="h-3 w-3" />
                              {call.duration_seconds}s
                            </Badge>
                          </TableCell>
                          <TableCell>{getActionBadge(call.action)}</TableCell>
                          <TableCell>{getSentimentBadge(call.sentiment)}</TableCell>
                          <TableCell>{getEsitoBadge(call.esito_chiamata || "N/A")}</TableCell>
                          <TableCell className="text-sm text-gray-600">{call.motivazione || "N/A"}</TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewCall(call)}
                              className="gap-1.5 hover:bg-blue-600 hover:text-white group-hover:translate-x-0.5 transform transition-all duration-200 font-medium h-8 px-3"
                            >
                              <FileText className="h-3.5 w-3.5" />
                              <span className="text-xs">Dettagli</span>
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
          {!isLoading && totalCalls > 0 && (
                <div className="flex flex-col sm:flex-row items-center justify-between mt-6 pt-4 border-t gap-4">
                  <div className="text-sm font-medium text-gray-600">
                    Mostrando <span className="text-gray-900 font-semibold">{(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, totalCalls)}</span> di{" "}
                    <span className="text-gray-900 font-semibold">{totalCalls}</span> chiamate
                  </div>
                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="h-9 gap-2 border-2 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      <span className="hidden sm:inline">Precedente</span>
                    </Button>
                    <div className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-blue-50 to-blue-100/50 rounded-lg border border-blue-200">
                      <span className="text-sm font-semibold text-blue-900">
                        {currentPage}
                      </span>
                      <span className="text-sm text-blue-600">/</span>
                      <span className="text-sm font-medium text-blue-700">
                        {totalPages}
                      </span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="h-9 gap-2 border-2 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
                    >
                      <span className="hidden sm:inline">Successiva</span>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
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
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-sm whitespace-pre-wrap">
                    {(selectedCall as any).summary || "Nessun summary disponibile"}
                  </pre>
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
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {(selectedCall as any).transcript || "Nessun transcript disponibile"}
                  </pre>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
