import React from "react";
import Header from "@/components/Header";
import NewAgentCom from "../components/NewAgent";
export default function NewAgent(){
      return(
            <>
                <Header title="ایجنت ها"  text="برای فعالیت های مختلف خود ایجنت طراحی کنید"/>
                <NewAgentCom />
            </>
      )
}