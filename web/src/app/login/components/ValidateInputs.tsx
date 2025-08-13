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
import EmailInput from "./EmailInput";
import PasswordInput from "./PasswordInput";
export type TFormValue = {
      email : string ;
      password : string ;
}
const schema = Yup.object({
      email : Yup.string().email("ایمیل معتبر نیست").required("ایمیل اجباری است") , 
      password : Yup.string().required("وارد کردن رمز عبور اجباری است")
})
export default function ValidateInputs(){
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
      <form onSubmit={handleSubmit(onSubmit)}>
            <div className="flex flex-col gap-6">
                 <LoginHeader title="ورود به نکسا" subTitle="حساب کاربری ندارید؟" headerLink="ثبت نام" />
            <div className="flex flex-col gap-6">
                <EmailInput name="email" register={register} error={errors.email?.message}/>
                <div className="grid gap-3">
                    <div className="flex justify-between">
                        <Label htmlFor="password">رمز عبور<span className="text-[#EF4444]">*</span></Label>
                        <Link href="/login/forgetpassword" className="text-sm hover:underline transition duration-500">رمز عبورتان را فراموش کردید؟</Link>
                    </div>
                    <PasswordInput register={register} name="password" error={errors.password?.message}/>

                </div>
                <Button type="submit" className="w-full cursor-pointer">
                    ورود
                </Button>
            </div>
            </div>
        </form>
            
            </>
      )
}