import React, { Suspense } from "react";
import ResetPasswordCom from "@/app/login/components/ResetPassword";
export default function ResetPassword(){
    return(
        <>
        <Suspense fallback={null}>
            <ResetPasswordCom />
        </Suspense>
        </>
    )
}