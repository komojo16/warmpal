import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "warmpal",
  description: "문자로 가족이 되는 AI 케어 서비스",
  manifest: "/manifest.json",
  themeColor: "#ff5a1f",
  other: {
    "mobile-web-app-capable": "yes",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "warmpal",
  },
  icons: {
    icon: "/warmpal-icon-1024.png",
    apple: "/icons/icon-192x192.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <Toaster
          position="top-center"
          toastOptions={{
            style: { fontFamily: "Noto Sans KR, sans-serif", fontSize: "14px" },
          }}
        />
        {children}
      </body>
    </html>
  );
}
