"use client";
import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import LoginHeader from "./LoginHeader";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import { useSearchParams } from "next/navigation";
import Swal from "sweetalert2";
export type TFormValue = {
  password: string;
  cpassword: string;
};
const schema = Yup.object({
  password: Yup.string().required("وارد کردن رمز عبور اجباری است").required(),
  cpassword: Yup.string()
    .oneOf([Yup.ref("password")], "رمز عبور خود را مجددا تکرار کنید")
    .required(),
});
type FormValues = Yup.InferType<typeof schema>;
const API_Base_Url = process.env.API_BASE_URL ?? "http://localhost:8000";
const End_point = "/reset-password";
export default function ResetPasswordCom() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const username = searchParams.get("username");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<FormValues>({
    mode: "onTouched",
    resolver: yupResolver(schema),
  });
  async function onSubmit(data: FormValues) {
    try {
      const respond = await fetch(
        `${API_Base_Url}${End_point}?token=${token}&username=${username}&new_password=${password}`,
        {
          method: "POST",
          headers: { "Content-type": "x-www-form-urlencoded" },
        }
      );

      if (!respond.ok) {
        Swal.fire({
          icon: "error",
          title: "خطا",
          text: "خطا به وجود آمد",
        });
        return;
      }
      Swal.fire({ icon: "success", title: "موفقیت" });
    } catch {
      console.log("خطایی رخ داده است");
    }
  }
  return (
    <>
      <LoginHeader
        title="تغییر رمز عبور"
        subTitle="رمز عبور خود را وارد کنید"
        headerLink=""
      />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="flex flex-col gap-6">
          <div className="grid gap-3">
            <Label htmlFor="password1">
              رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="password1" type="password" {...register("password")} />
          </div>
          <div className="grid gap-3">
            <Label htmlFor="repeat-password">
              تکرار رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <Input
              id="repeat-password"
              type="password"
              {...register("cpassword")}
            />
            {errors.cpassword && (
              <p className="text-xs text-red-400">{errors.cpassword.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full cursor-pointer">
            ذخیره رمز عبور
          </Button>
        </div>
      </form>
    </>
  );
}
