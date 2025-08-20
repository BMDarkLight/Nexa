import React from "react";
import LoginStructure from "@/app/login/components/LoginStructure";

export default function RootLayout({children,}: Readonly<{ children: React.ReactNode; }>) {
    return (
        <LoginStructure>
            {children}
        </LoginStructure>
    );
}
