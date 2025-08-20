"use client"
import { usePathname } from "next/navigation";
import React from "react";
interface IH2Prop{
      title: string ; 
}
const TypeH2Tag = [{url:"/agent"} ,{url:"/connector"}]
export default function H2Tag(){
      const pathname = usePathname()
      const handleH2tag = ()=>{
            if(pathname == "agent"){
                  console.log(pathname);
                  
            }
      }
      return(
            <>
              {handleH2tag} 
            </>
      )
}