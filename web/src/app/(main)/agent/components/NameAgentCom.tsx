import React from "react";
import ReturnBtn from "./ReturnBtn";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import RedirectBtn from "./RedirectBtn";
export default function NameAgentCom(){
      return(
            <>
                <div className="flex flex-col justify-between gap-5 lg:px-5 h-[100vh] md:h-auto">
                 <div className="flex flex-col gap-5">
                   <h2 className="text-xl font-medium mt-5 md:mt-0">اطلاعات ایجنت را وارد کنید</h2>
                  <div className="w-full md:w-[80%]">
                        <Label htmlFor="name-agent" className="mb-3">نام ایجنت</Label>
                      <Input  id="name-agent" type="text" placeholder="نام ایجنت"/>     
                  </div>
                 </div>
                  <div className="flex justify-end items-center gap-3">
                        <ReturnBtn/>
                        <RedirectBtn />
                  </div>
               </div>
            
            </>
      )
}