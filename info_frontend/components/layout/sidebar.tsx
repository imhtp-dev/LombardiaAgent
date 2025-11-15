"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Brain,
  CheckSquare,
  Users,
  Mic,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const menuItems = [
  {
    title: "Riepilogo",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Conoscenza AI",
    href: "/dashboard/conoscenza",
    icon: Brain,
  },
  {
    title: "Check Conoscenza",
    href: "/dashboard/verifica-conoscenza",
    icon: CheckSquare,
  },
  {
    title: "Gestione Utenti",
    href: "/dashboard/utenti",
    icon: Users,
  },
  {
    title: "Voilà Voice",
    href: "/dashboard/voiceagent",
    icon: Mic,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Menu Button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
      </Button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen w-64 bg-gradient-to-b from-white to-gray-50/30 border-r border-gray-200/60 transition-transform duration-300 ease-in-out lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-center h-16 border-b border-gray-200/60 px-6 bg-white/80 backdrop-blur-sm">
            <Link href="/dashboard" className="flex items-center gap-3 group">
              <div className="relative w-10 h-10 transform group-hover:scale-110 transition-transform duration-300">
                <Image
                  src="/images/Voila_matita.png"
                  alt="Voilà Voice"
                  fill
                  className="object-contain drop-shadow-md"
                />
              </div>
              <span className="text-lg font-bold bg-gradient-to-r from-blue-600 via-blue-700 to-blue-800 bg-clip-text text-transparent">
                Voilà Voice
              </span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-6 px-3">
            <ul className="space-y-1.5">
              {menuItems.map((item, index) => {
                const isActive = pathname === item.href;
                return (
                  <li 
                    key={item.href}
                    className="animate-in slide-in-from-left duration-300"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <Link
                      href={item.href}
                      onClick={() => setIsOpen(false)}
                      className={cn(
                        "group relative flex items-center gap-3 px-4 py-3.5 rounded-xl font-medium transition-all duration-200 overflow-hidden",
                        isActive
                          ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-200"
                          : "text-gray-700 hover:bg-gradient-to-r hover:from-gray-100 hover:to-gray-50 hover:text-gray-900 hover:shadow-sm"
                      )}
                    >
                      {/* Active indicator */}
                      {isActive && (
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-white rounded-r-full"></div>
                      )}
                      
                      {/* Icon with background */}
                      <div className={cn(
                        "p-1.5 rounded-lg transition-all duration-200",
                        isActive 
                          ? "bg-white/20" 
                          : "bg-gray-100 group-hover:bg-white group-hover:shadow-sm"
                      )}>
                        <item.icon className={cn(
                          "h-5 w-5 transition-transform duration-200",
                          isActive ? "scale-110" : "group-hover:scale-110"
                        )} />
                      </div>
                      
                      <span className="text-[15px]">{item.title}</span>
                      
                      {/* Hover shine effect */}
                      {!isActive && (
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700"></div>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Footer */}
          <div className="border-t border-gray-200/60 p-4 bg-white/50 backdrop-blur-sm">
            <p className="text-xs text-center text-gray-500 font-medium">
              © 2025 Voilà Voice
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
