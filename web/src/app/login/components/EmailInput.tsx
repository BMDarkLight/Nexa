import React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Path, UseFormRegister } from "react-hook-form";
type Props<T> = {
  name: Path<T>;
  register: UseFormRegister<any>;
  error?: string;
};
export default function EmailInput<T>({ register, error, name }: Props<T>) {
  return (
    <>
      <div className="grid gap-3">
        <Label htmlFor="email">
          نام کاربری<span className="text-[#EF4444]">*</span>
        </Label>
        <Input type="text" />
      </div>
    </>
  );
}
