"use client"
import React, { useState } from "react";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";
import {Button} from "@/components/ui/button";
import Link from "next/link";
import LoginHeader from "@/app/login/components/LoginHeader";
import {useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import Swal from "sweetalert2";
import Cookie from "js-cookie";
interface IUserData {
  username: string;
  password: string;
  firstname: string;
  lastname: string;
  email: string;
  phone: string;
  organization: string;
  plan: string;
  token?: string;
}
export type TFormValue = {
      username : string ;
}
const schema = Yup.object({
      username : Yup.string().required("این فیلد اجباری است") 
})
export default function ForgetPasswordCom(){
     const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
        reset
      } = useForm<TFormValue>({
          resolver: yupResolver(schema)
      })
      const API_Base_Url = process.env.API_BASE_URL ?? "http://localhost:8000" ; 
      const End_point = "/forget-password" ;
        const onSubmit = async (data: TFormValue) => {
    try {
      const checkRes = await fetch(
        `${API_Base_Url}${End_point}?username=${encodeURIComponent(data.username)}}`
      );
      const matchedUsers: IUserData[] = await checkRes.json();

      if (matchedUsers.length === 0) {
        Swal.fire({ icon: "error", title: "خطا", text: "نام کاربری یا رمز عبور اشتباه است!" });
        return;
      }

         const newUserData: IUserData = {
        username: data.username,
        password: "",
        firstname: "",
        lastname: "",
        email: "",
        phone: "",
        organization: "string",
        plan: "free"
      };

      const postRes = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUserData)
      });

      if (!postRes.ok) {
        Swal.fire({ icon: "error", title: "خطا", text: "ثبت کاربر با مشکل مواجه شد" });
        return;
      }


      const loginRes = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: data.username
        }),
      });


      if (!loginRes.ok) {
        console.log("failed to get token");
        return;
      }

      const { access_token, token_type } = await loginRes.json();

      Cookie.set("auth_token", access_token, { expires: 7, secure: true, sameSite: "strict" });
      Cookie.set("token_type", token_type, { expires: 7, secure: true, sameSite: "strict" });

      Swal.fire({ icon: "success", title: "موفق", text: "ورود موفقیت‌آمیز!" });
      reset();
    } catch (err) {
      Swal.fire({ icon: "error", title: "خطا", text: err instanceof Error ? err.message : "خطای ناشناخته" });
    }
  };
    return(
        <>
                <LoginHeader title="فراموشی رمز عبور"  subTitle="ایمیل خود را وارد کنید" headerLink="" />
                <form onSubmit={handleSubmit(onSubmit)}>
                    <div className="flex flex-col gap-6">
                        
                        <div className="grid gap-3">
                            <Label htmlFor="username">نام کاربری<span className="text-[#EF4444]">*</span></Label>
                            <Input
                                id="username"
                                type="text"
                                placeholder="m@example.com"
                                {...register("username")}
                            />
                        </div>
                        <Button type="submit" className="w-full cursor-pointer">
                            دریافت لینک تغییر رمز
                        </Button>
                    </div>
                </form>
        </>
    )
}