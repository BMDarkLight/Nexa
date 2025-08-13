"use client";
import React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import LoginHeader from "@/app/login/components/LoginHeader";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
export type TFormValue = {
  password: string;
  cpassword: string;
};
const schema = Yup.object().shape({
  password: Yup.string().required("وارد کردن رمز عبور اجباری است"),
  cpassword: Yup.string().oneOf(
    [Yup.ref("password")],
    "رمز عبور خود را مجددا تکرار کنید"
  ),
});
export default function ResetPasswordCom() {
  return (
    <>
      <LoginHeader
        title="تغییر رمز عبور"
        subTitle="رمز عبور خود را وارد کنید"
        headerLink=""
      />
      <form>
        <div className="flex flex-col gap-6">
          <div className="grid gap-3">
            <Label htmlFor="password1">
              رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="password1" type="password" />
          </div>
          <div className="grid gap-3">
            <Label htmlFor="repeat-password">
              تکرار رمز عبور جدید<span className="text-[#EF4444]">*</span>
            </Label>
            <Input id="repeat-password" type="password" />
          </div>
          <Button type="submit" className="w-full cursor-pointer">
            ذخیره رمز عبور
          </Button>
        </div>
      </form>
    </>
  );
}
