"use client";

import { useState, useEffect } from "react";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  UserPlus,
  Search,
  RefreshCw,
  Mail,
  ToggleLeft,
  ToggleRight,
  Trash2,
  AlertCircle,
  CheckCircle,
  Users,
  User,
  AtSign,
  Shield,
  Calendar,
  Activity,
  Loader2,
} from "lucide-react";
import { usersApi, type User as UserType } from "@/lib/api-client";

export default function UtentiPage() {
  const [nome, setNome] = useState("");
  const [cognome, setCognome] = useState("");
  const [email, setEmail] = useState("");
  const [ruolo, setRuolo] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterRole, setFilterRole] = useState("all");
  const [alert, setAlert] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  // Real data state
  const [users, setUsers] = useState<UserType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Load users on mount
  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch (err) {
      console.error("Error loading users:", err);
      showAlert("Errore nel caricamento degli utenti", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const showAlert = (message: string, type: "success" | "error" | "info") => {
    setAlert({ message, type });
    setTimeout(() => setAlert(null), 5000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!nome.trim() || !cognome.trim() || !email.trim() || !ruolo) {
      showAlert("Tutti i campi sono obbligatori", "error");
      return;
    }
    
    setIsSaving(true);
    try {
      const result = await usersApi.create({
        nome: nome.trim(),
        cognome: cognome.trim(),
        email: email.trim(),
        ruolo: ruolo,
      });
      
      showAlert(
        result.email_sent 
          ? "Utente creato con successo! Credenziali inviate via email." 
          : "Utente creato, ma email non inviata. Controlla configurazione SendGrid.",
        result.email_sent ? "success" : "info"
      );
      
      // Clear form
      setNome("");
      setCognome("");
      setEmail("");
      setRuolo("");
      
      // Reload users
      await loadUsers();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore durante la creazione dell'utente";
      showAlert(errorMessage, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.cognome.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === "all" || user.ruolo === filterRole;
    return matchesSearch && matchesRole;
  });

  const handleToggleStatus = async (userId: number, currentStatus: boolean) => {
    const action = currentStatus ? "disattivare" : "attivare";
    if (!confirm(`Sei sicuro di voler ${action} questo utente?`)) {
      return;
    }
    
    try {
      await usersApi.toggleStatus(userId);
      showAlert(`Utente ${action === "disattivare" ? "disattivato" : "attivato"} con successo!`, "success");
      await loadUsers();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore durante il cambio stato";
      showAlert(errorMessage, "error");
    }
  };

  const handleResendCredentials = async (userId: number) => {
    if (!confirm("Sei sicuro di voler rinviare le credenziali a questo utente?")) {
      return;
    }
    
    try {
      const result = await usersApi.resendCredentials(userId);
      showAlert(
        result.email_sent
          ? "Credenziali rinviate con successo!"
          : "Credenziali generate ma email non inviata",
        result.email_sent ? "success" : "info"
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore durante l'invio";
      showAlert(errorMessage, "error");
    }
  };

  const handleDelete = async (userId: number) => {
    if (!confirm("Sei sicuro di voler eliminare questo utente? Questa azione non può essere annullata.")) {
      return;
    }
    
    try {
      await usersApi.delete(userId);
      showAlert("Utente eliminato con successo!", "success");
      await loadUsers();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Errore durante l'eliminazione";
      showAlert(errorMessage, "error");
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Gestione Utenti</h1>
        <p className="text-muted-foreground mt-1">
          Crea e gestisci gli utenti del sistema
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

      {/* Create User Form */}
      <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-blue-600" />
            Nuovo Utente
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="nome" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Nome
                </Label>
                <Input
                  id="nome"
                  placeholder="Nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="border-gray-200 hover:border-blue-300 transition-colors"
                  disabled={isSaving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cognome" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Cognome
                </Label>
                <Input
                  id="cognome"
                  placeholder="Cognome"
                  value={cognome}
                  onChange={(e) => setCognome(e.target.value)}
                  className="border-gray-200 hover:border-blue-300 transition-colors"
                  disabled={isSaving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <AtSign className="h-4 w-4" />
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="nome@esempio.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="border-gray-200 hover:border-blue-300 transition-colors"
                  disabled={isSaving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ruolo" className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Ruolo
                </Label>
                <Select value={ruolo} onValueChange={setRuolo} disabled={isSaving}>
                  <SelectTrigger id="ruolo" className="border-gray-200 hover:border-blue-300 transition-colors">
                    <SelectValue placeholder="Seleziona Ruolo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="master">Master User</SelectItem>
                    <SelectItem value="Piemonte">Piemonte User</SelectItem>
                    <SelectItem value="Lombardia">Lombardia User</SelectItem>
                    <SelectItem value="Veneto">Veneto User</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button type="submit" className="gap-2 hover:scale-105 transition-transform" disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creazione...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  Invia Accessi
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card className="border-gray-100 shadow-sm hover:shadow-md transition-all">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-600" />
              Utenti Registrati
              <Badge variant="secondary" className="gap-1">
                <Activity className="h-3 w-3" />
                {filteredUsers.length}
              </Badge>
            </CardTitle>
            <Button variant="outline" size="sm" onClick={loadUsers} className="gap-2 hover:scale-105 transition-transform" disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Aggiorna
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Search and Filter */}
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Cerca utenti..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 border-gray-200 hover:border-blue-300 transition-colors"
                />
              </div>
            </div>
            <Select value={filterRole} onValueChange={setFilterRole}>
              <SelectTrigger className="w-full sm:w-[180px] border-gray-200 hover:border-blue-300 transition-colors">
                <SelectValue placeholder="Tutti i ruoli" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutti i ruoli</SelectItem>
                <SelectItem value="master">Master</SelectItem>
                <SelectItem value="Piemonte">Piemonte</SelectItem>
                <SelectItem value="Lombardia">Lombardia</SelectItem>
                <SelectItem value="Veneto">Veneto</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Loading State */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : (
            <div className="rounded-lg border border-gray-100 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50/50 hover:bg-gray-50/50">
                    <TableHead className="font-semibold">Nome</TableHead>
                    <TableHead className="font-semibold">Email</TableHead>
                    <TableHead className="font-semibold">Ruolo</TableHead>
                    <TableHead className="font-semibold">Stato</TableHead>
                    <TableHead className="font-semibold">Data Creazione</TableHead>
                    <TableHead className="font-semibold">Azioni</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        Nessun utente trovato
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredUsers.map((user) => (
                      <TableRow key={user.user_id} className="hover:bg-blue-50/50 transition-colors">
                        <TableCell className="font-medium">
                          {user.nome} {user.cognome}
                        </TableCell>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell>
                          <Badge
                            variant={user.ruolo === "master" ? "default" : "secondary"}
                            className="gap-1"
                          >
                            <Shield className="h-3 w-3" />
                            {user.ruolo}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={`gap-1 ${
                              user.is_active
                                ? "bg-green-100 text-green-800 hover:bg-green-200"
                                : "bg-red-100 text-red-800 hover:bg-red-200"
                            }`}
                          >
                            <Activity className="h-3 w-3" />
                            {user.is_active ? "Attivo" : "Inattivo"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-sm">
                            <Calendar className="h-3 w-3 text-muted-foreground" />
                            {new Date(user.created_at).toLocaleDateString("it-IT")}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleResendCredentials(user.user_id)}
                              title="Rinvia credenziali"
                              className="hover:bg-blue-50 hover:text-blue-700 hover:scale-110 transition-all"
                            >
                              <Mail className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleStatus(user.user_id, user.is_active)}
                              title={user.is_active ? "Disattiva" : "Attiva"}
                              className="hover:bg-yellow-50 hover:text-yellow-700 hover:scale-110 transition-all"
                            >
                              {user.is_active ? (
                                <ToggleRight className="h-4 w-4" />
                              ) : (
                                <ToggleLeft className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(user.user_id)}
                              className="text-red-600 hover:bg-red-50 hover:text-red-700 hover:scale-110 transition-all"
                              title="Elimina"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
