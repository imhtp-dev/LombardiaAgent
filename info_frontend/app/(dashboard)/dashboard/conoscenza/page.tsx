"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Search,
  RefreshCw,
  Save,
  RotateCcw,
  Edit2,
  Trash2,
  X,
  AlertCircle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Plus,
  Brain,
  MapPin,
  Calendar,
  User as UserIcon,
  FileText,
  Filter,
} from "lucide-react";
import { dummyQAEntries, dummyRegions } from "@/lib/dummy-data";

export default function ConoscenzaPage() {
  const [selectedRegion, setSelectedRegion] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("created_at_desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [alert, setAlert] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  
  const itemsPerPage = 6;

  const filteredQA = dummyQAEntries.filter((qa) => {
    if (!selectedRegion) return false;
    if (selectedRegion !== "All Region" && qa.region !== selectedRegion) return false;
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        qa.question.toLowerCase().includes(search) ||
        qa.answer.toLowerCase().includes(search) ||
        qa.id_domanda.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const totalPages = Math.ceil(filteredQA.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedQA = filteredQA.slice(startIndex, startIndex + itemsPerPage);

  const showAlert = (message: string, type: "success" | "error" | "info") => {
    setAlert({ message, type });
    setTimeout(() => setAlert(null), 5000);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRegion) {
      showAlert("Seleziona una regione prima di salvare", "error");
      return;
    }
    if (!question.trim() || !answer.trim()) {
      showAlert("Domanda e risposta sono obbligatorie", "error");
      return;
    }
    
    if (editingId) {
      showAlert("Domanda modificata con successo!", "success");
    } else {
      showAlert("Nuova domanda aggiunta con successo!", "success");
    }
    handleReset();
  };

  const handleEdit = (qa: typeof dummyQAEntries[0]) => {
    setEditingId(qa.qa_id);
    setQuestion(qa.question);
    setAnswer(qa.answer);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = (id: number) => {
    if (confirm("Sei sicuro di voler eliminare questa domanda e risposta?")) {
      showAlert("Domanda eliminata con successo!", "success");
    }
  };

  const handleReset = () => {
    setQuestion("");
    setAnswer("");
    setEditingId(null);
  };

  if (!selectedRegion) {
    return (
      <div className="space-y-6 animate-in fade-in duration-700">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Conoscenza AI</h1>
          <p className="text-muted-foreground mt-1">
            Gestisci domande e risposte per il voice agent
          </p>
        </div>

        <Card className="border-gray-100 shadow-sm">
          <CardContent className="pt-6">
            <div className="space-y-2">
              <Label htmlFor="region" className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Seleziona Regione
              </Label>
              <Select value={selectedRegion} onValueChange={setSelectedRegion}>
                <SelectTrigger id="region" className="border-gray-200 hover:border-blue-300 transition-colors">
                  <SelectValue placeholder="Seleziona una regione" />
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
          </CardContent>
        </Card>

        <Card className="border-blue-100 bg-blue-50/30 shadow-sm">
          <CardContent className="pt-6 text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-100 flex items-center justify-center">
              <Brain className="h-8 w-8 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Seleziona una regione</h3>
            <p className="text-muted-foreground text-sm">
              Seleziona una regione dal menu sopra per visualizzare e gestire le domande e risposte
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Conoscenza AI</h1>
          <p className="text-muted-foreground mt-1 flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            {selectedRegion} • {filteredQA.length} domande
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => setSelectedRegion("")}
          className="gap-2 hover:scale-105 transition-transform"
        >
          <RotateCcw className="h-4 w-4" />
          Cambia Regione
        </Button>
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

      {/* Add/Edit Form */}
      <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {editingId ? <Edit2 className="h-5 w-5 text-blue-600" /> : <Plus className="h-5 w-5 text-blue-600" />}
            {editingId ? "Modifica Domanda e Risposta" : "Aggiungi Nuova Domanda e Risposta"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="question" className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Domanda
                </Label>
                <Textarea
                  id="question"
                  placeholder="Inserisci la domanda..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  rows={5}
                  className="resize-none border-gray-200 hover:border-blue-300 transition-colors"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="answer" className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  Risposta
                </Label>
                <Textarea
                  id="answer"
                  placeholder="Inserisci la risposta..."
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  rows={5}
                  className="resize-none border-gray-200 hover:border-blue-300 transition-colors"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" className="gap-2 hover:scale-105 transition-transform">
                <Save className="h-4 w-4" />
                {editingId ? "Aggiorna" : "Salva"}
              </Button>
              <Button type="button" variant="outline" onClick={handleReset} className="gap-2 hover:scale-105 transition-transform">
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
              {editingId && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  className="gap-2 hover:scale-105 transition-transform"
                >
                  <X className="h-4 w-4" />
                  Annulla
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Search and Filter */}
      <Card className="border-gray-100 shadow-sm">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Cerca nelle domande e risposte..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="pl-10 border-gray-200 hover:border-blue-300 transition-colors"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-full sm:w-[200px] border-gray-200 hover:border-blue-300 transition-colors">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at_desc">Più recenti</SelectItem>
                  <SelectItem value="created_at_asc">Più vecchie</SelectItem>
                  <SelectItem value="updated_at_desc">Ultime modificate</SelectItem>
                  <SelectItem value="question_asc">Domanda A-Z</SelectItem>
                  <SelectItem value="question_desc">Domanda Z-A</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" className="gap-2 hover:scale-105 transition-transform">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Q&A Cards */}
      {paginatedQA.length === 0 ? (
        <Card className="border-dashed border-gray-200">
          <CardContent className="pt-6 text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <Search className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Nessuna domanda trovata</h3>
            <p className="text-muted-foreground text-sm">
              {searchTerm
                ? "Prova a modificare i criteri di ricerca"
                : "Aggiungi la prima domanda usando il form sopra"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedQA.map((qa) => (
              <Card key={qa.qa_id} className="flex flex-col border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all hover:-translate-y-1">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <Badge variant="outline" className="mb-2 gap-1">
                        <FileText className="h-3 w-3" />
                        {qa.id_domanda}
                      </Badge>
                      <CardTitle className="text-base line-clamp-2">
                        {qa.question}
                      </CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 pb-3">
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {qa.answer}
                  </p>
                </CardContent>
                <CardFooter className="flex-col items-stretch gap-2 pt-3 border-t">
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-3 w-3" />
                    {new Date(qa.created_at).toLocaleDateString("it-IT")}
                    {qa.created_by && (
                      <>
                        <UserIcon className="h-3 w-3 ml-1" />
                        {qa.created_by}
                      </>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 gap-2 hover:bg-blue-50 hover:text-blue-700 hover:scale-105 transition-all"
                      onClick={() => handleEdit(qa)}
                    >
                      <Edit2 className="h-3 w-3" />
                      Modifica
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 gap-2 text-red-600 hover:bg-red-50 hover:text-red-700 hover:scale-105 transition-all"
                      onClick={() => handleDelete(qa.qa_id)}
                    >
                      <Trash2 className="h-3 w-3" />
                      Elimina
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-sm text-muted-foreground">
                Mostrando {startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredQA.length)} di{" "}
                {filteredQA.length} risultati
              </p>
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
                <span className="text-sm font-medium px-3">
                  Pagina {currentPage} di {totalPages}
                </span>
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
    </div>
  );
}
