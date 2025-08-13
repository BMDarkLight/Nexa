"use client"
import React from "react";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";
import {Button} from "@/components/ui/button";
import Link from "next/link";
import LoginHeader from "@/app/login/components/LoginHeader";
import {useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
export type TFormValue = {
      email : string ;
}
const schema = Yup.object({
      email : Yup.string().email("ایمیل معتبر نیست").required("ایمیل اجباری است") 
})
export default function ForgetPasswordCom(){
     const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
      } = useForm<TFormValue>({
          resolver: yupResolver(schema)
      })
      const onSubmit = (data : TFormValue) =>{
          console.log(data);
      }
    return(
        <>
                <LoginHeader title="فراموشی رمز عبور"  subTitle="ایمیل خود را وارد کنید" headerLink="" />
                <form onSubmit={handleSubmit(onSubmit)}>
                    <div className="flex flex-col gap-6">
                        
                        <div className="grid gap-3">
                            <Label htmlFor="email">ایمیل<span className="text-[#EF4444]">*</span></Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="m@example.com"
                                {...register("email")}
                            />
                            {errors.email && (
                                <p className="text-xs text-red-400">{errors.email.message}</p>
                            )}
                        </div>
                        <Button type="submit" className="w-full cursor-pointer">
                            دریافت لینک تغییر رمز
                        </Button>
                    </div>
                </form>
        </>
    )
}