"use client"
import React, { useState } from "react";
import { Bot, EllipsisVertical, Plus, Trash2 } from "lucide-react";
import Swal from "sweetalert2";
export default function DeleteAgent(){
      const [show , setShow] = useState(false);
      const handleDeleteAgent = async ()=>{
            const result = await Swal.fire({
                  title : "حذف ایجنت" ,
      text: "آیا مطمئن هستید که می‌خواهید ایجنت فلان را حذف کنید؟",
      showCancelButton: true,
      cancelButtonText: "انصراف",
      confirmButtonText: "خروج",
      reverseButtons : true ,
      customClass : {
        popup : "swal-rtl" ,
        title : "swal-title" , 
        confirmButton : "swal-confirm-btn swal-half-btn" , 
        cancelButton : "swal-cancel-btn swal-half-btn" ,
        htmlContainer : "swal-text" , 
        actions : "swal-container"
      }
            })
      }
      return(
            <>
                <div className=" absolute top-0 right-[90%] cursor-pointer">
                              <EllipsisVertical size={20} onClick={()=>setShow(!show)} />
                              <div className={`flex justify-between items-center w-40 rounded-md px-3 py-2 absolute top-[-40px] right-[5px] bg-white shadow-md hover:text-[#DC2626] transition duration-400 ${show ? `block` : `hidden`}`} onClick={handleDeleteAgent}>
                                    <p className="text-sm">حذف</p>
                                    <Trash2 size={16} />
                              </div>
                        </div>
            
            
            </>
      )
}