"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut, User, ChevronDown } from "lucide-react";
import { getCurrentUser, authApi } from "@/lib/api-client";
import { useRouter } from "next/navigation";

export function Navbar() {
  const router = useRouter();
  const [userName, setUserName] = useState<string>("");
  const [userEmail, setUserEmail] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("Master");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const user = getCurrentUser();
    if (user) {
      setUserName(user.name);
      setUserEmail(user.email);

      // Map role to display text
      if (user.role === "admin" || user.region === "master") {
        setUserRole("Master");
      } else if (user.region === "Lombardia") {
        setUserRole("Lombardia");
      } else {
        setUserRole(user.region || "Operator");
      }
    }
    setIsLoading(false);
  }, []);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      // Clear local storage
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      router.push("/login");
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b px-6 flex items-center justify-end lg:justify-end">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="flex items-center gap-3 px-3 py-2 h-auto hover:bg-gray-50"
          >
            <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-200">
              <Image
                src="/images/sagoma.png"
                alt="User"
                fill
                className="object-cover"
              />
            </div>
            <div className="hidden sm:flex flex-col items-start">
              <span className="text-sm font-medium">
                {isLoading ? "Caricamento..." : userName || "Utente"}
              </span>
              <span className="text-xs text-muted-foreground">{userRole}</span>
            </div>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">
                {isLoading ? "Caricamento..." : userName || "Utente"}
              </p>
              <p className="text-xs leading-none text-muted-foreground">
                {userEmail || ""}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer">
            <User className="mr-2 h-4 w-4" />
            <span>Profilo</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="cursor-pointer text-red-600 focus:text-red-600"
            onClick={handleLogout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            <span>Logout</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
