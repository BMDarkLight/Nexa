import React from "react";
import LoginStructure from "@/app/login/components/LoginStructure";

export default function RootLayout({children,}: Readonly<{ children: React.ReactNode; }>) {
    return (
        <html lang="en" dir="rtl">
        <body>
        <LoginStructure>
            {children}
        </LoginStructure>
        </body>
        </html>
    );
}
