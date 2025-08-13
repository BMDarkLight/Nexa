import React from "react";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";
import { Path , UseFormRegister } from "react-hook-form";
import Link from "next/link";
type Props<T> = {
      name : Path<T>
      register : UseFormRegister<any>;
      error? : string ;
}
export default function PasswordInput<T>({register , error , name} : Props<T>){
      return(
            <>
                    <Input
                        id="password"
                        type="password"
                        {...register(name)}
                    />
                    {error && <p className="text-xs text-red-400">{error}</p>}
            </>
      )
}