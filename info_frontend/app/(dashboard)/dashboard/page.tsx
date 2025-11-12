"use client";

import { useState } from "react";
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
  LucideIcon
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import {
  dummyDashboardStats,
  dummySentimentStats,
  dummyActionStats,
  dummyCallOutcomeStats,
  dummyRecentCalls,
  dummyRegions,
  dummyOutcomeTrend,
  dummySentimentTrend,
} from "@/lib/dummy-data";
import { Call } from "@/types";

export default function DashboardPage() {
  const [selectedRegion, setSelectedRegion] = useState("All Region");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const totalPages = Math.ceil(dummyRecentCalls.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedCalls = dummyRecentCalls.slice(startIndex, endIndex);

  const handleClearFilters = () => {
    setStartDate("");
    setEndDate("");
    setSelectedRegion("All Region");
  };

  const handleViewCall = (call: Call) => {
    setSelectedCall(call);
    setIsModalOpen(true);
  };

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
    const config = variants[sentiment] || { className: "", icon: Activity };
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
                  {dummyRegions.map((region) => (
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
                <Button variant="default" className="flex-1 gap-2 hover:scale-105 transition-transform">
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

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Totale Minuti"
          value={`${dummyDashboardStats.totalMinutes.toLocaleString()} min`}
          icon={Clock}
          iconColor="text-blue-600"
        />
        <StatCard
          title="Corrispettivo Euro"
          value={`€ ${dummyDashboardStats.totalRevenue.toFixed(2)}`}
          icon={Euro}
          iconColor="text-green-600"
        />
        <StatCard
          title="Nr. Chiamate"
          value={dummyDashboardStats.totalCalls.toLocaleString()}
          icon={Phone}
          iconColor="text-purple-600"
        />
        <StatCard
          title="Durata Media"
          value={`${dummyDashboardStats.avgDuration} min`}
          icon={TrendingUp}
          iconColor="text-yellow-600"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
                  data={dummySentimentStats}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.sentiment}
                  outerRadius={70}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {dummySentimentStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

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
                  data={dummyActionStats}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.action}
                  outerRadius={70}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {dummyActionStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <PieChartIcon className="h-5 w-5 text-blue-600" />
              Esiti Chiamate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={dummyCallOutcomeStats}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.esito}
                  outerRadius={70}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {dummyCallOutcomeStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Trend Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              Trend Esiti Chiamate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dummyOutcomeTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} name="Chiamate" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-600" />
              Trend Sentiment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dummySentimentTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} name="Sentiment" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

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
              {dummyRecentCalls.length} chiamate
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
                {paginatedCalls.map((call) => (
                  <TableRow key={call.id} className="hover:bg-blue-50/50 transition-colors">
                    <TableCell className="font-medium">{call.id}</TableCell>
                    <TableCell className="text-sm">
                      {new Date(call.started_at).toLocaleString("it-IT")}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {call.phone_number}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="gap-1">
                        <Clock className="h-3 w-3" />
                        {call.duration_seconds}s
                      </Badge>
                    </TableCell>
                    <TableCell>{getActionBadge(call.action)}</TableCell>
                    <TableCell>{getSentimentBadge(call.sentiment)}</TableCell>
                    <TableCell>{getEsitoBadge(call.esito_chiamata)}</TableCell>
                    <TableCell className="text-sm">{call.motivazione}</TableCell>
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
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between mt-4 gap-4">
            <div className="text-sm text-muted-foreground">
              Mostrando {startIndex + 1}-{Math.min(endIndex, dummyRecentCalls.length)} di{" "}
              {dummyRecentCalls.length} chiamate
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
                    <code className="text-sm bg-white px-2 py-1 rounded">{selectedCall.call_id}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Durata:</strong>
                    <span className="text-sm">{selectedCall.duration_seconds}s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Telefono:</strong>
                    <span className="text-sm font-mono">{selectedCall.phone_number}</span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  Summary disponibile per chiamate con analisi completa.
                </p>
              </TabsContent>
              <TabsContent value="intent" className="space-y-4 mt-4">
                <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Esito:</strong>
                    {getEsitoBadge(selectedCall.esito_chiamata)}
                  </div>
                  <div className="flex items-center gap-2">
                    <strong className="text-sm">Motivazione:</strong>
                    <span className="text-sm">{selectedCall.motivazione}</span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  Patient intent disponibile per chiamate dal 26/09/2024.
                </p>
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
