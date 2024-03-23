import arm_helpers

def printIClassTable(ofile, level, iclass):

    classes_list = []
    decoder_list = []
    
    for field in iclass["fields"]:
        print("    " * level + 
              "uint32_t "+ field["name"] + 
                " = EXTRACT_BITS(" + str(field["offset"]) +", "+ str(field["width"]) + ");", 
                file=ofile)
        
    already_has_condition = ""

    for row in iclass["tables"]["rows"]:
        
        encoded_name = "ENC_" + row["encname"]
       
        if row["undef"]: name = "return __UNALLOCATED(" + encoded_name + ");"
        elif row["unpred"]: name = "return __UNPREDICTABLE(" + encoded_name + ");"
        elif row["nop"]: name = "return __NOP(" + encoded_name + ");"
        else:
            name = "return decode_section_" + row["iformfile"] + "(context);" 
            decoder_list.append(row["iformfile"])
        
        classes_list.append(encoded_name)

        condition_string = ""
        for idx in range(0, len(row["patterns"])):

            if len(condition_string):
                condition_string += " && "

            condition_string += arm_helpers.createMaskCondition(
                            iclass["tables"]["headers"][idx], 
                            row["patterns"][idx]["mask"], 
                            row["patterns"][idx]["equal"]
                        )
        
        if len(condition_string):
            print( "    "*(level) + already_has_condition + "if(" + condition_string + ") " + name + " //" + row["encname"], file=ofile)
            already_has_condition = "else "
        else:
            print( "    "*(level) + name + " //" + row["encname"], file=ofile)
        
    
    print("    " * (level) + "return DECODE_ERROR;", file=ofile)

    return (classes_list, decoder_list)


def printGroupTree(ofile, classes, level, root):

    classes_list = []
    decoder_list = []

    print("    " * level + "// GROUP:"+ root["groupname"], file=ofile)

    for field in root["regdiagram"]["fields"]:
        print("    "*level + field["name"] + " = EXTRACT_BITS(" +
               str(field["offset"]) + ", "+ 
               str(field["width"]) + ");", file=ofile)

    already_has_condition = ""

    for children in root["children"]:
        
        if children["is_group"]:
            condition_string = ""
            for dec in children["decode"]:
                
                if len(condition_string):
                    condition_string += " && "

                condition_string += arm_helpers.createMaskCondition(
                        dec["name"], 
                        dec["mask"], 
                        dec["equal"]
                    )

            print( "    "*(level) + already_has_condition + "if(" + condition_string + ") {", file=ofile)
            (classes_, decoders_) = printGroupTree(ofile, classes, level + 1, children["group"])
            classes_list += classes_ 
            decoder_list += decoders_ 
            
            print( "    "*(level) + "}", file=ofile) 

            already_has_condition = "else "
        else:
            class_desc = children["iclass"]
            
            if class_desc["allocated"] and class_desc["predictable"]:
               
                class_object = classes[class_desc["class_name"]]

                condition_string = ""
                for dec in children["decode"]:

                    if len(condition_string):
                        condition_string += " && "

                    condition_string += arm_helpers.createMaskCondition(
                                                    dec["name"],
                                                    dec["mask"], 
                                                    dec["equal"]
                                                )

                print( "    " * (level) + already_has_condition + "if(" + condition_string + ") {", file=ofile)
                print( "    " * (level) + "// ICLASS:" + class_desc["class_name"], file=ofile)
                
                (classes_, decoders_) = printIClassTable(ofile, level + 1, class_object)
                classes_list += classes_ 
                decoder_list += decoders_ 
                print( "    "  * (level) + "}", file=ofile) 

                already_has_condition = "else "
            else:
                fallback_name = ""

                encoded_name = "ENC_" + class_desc["class_name"]

                if not class_desc["allocated"]: fallback_name = "return __UNPREDICTABLE(" + encoded_name + ");" 
                if not class_desc["predictable"]: fallback_name = "return __UNALLOCATED(" + encoded_name + ");"

                classes_list.append(encoded_name)

                condition_string = ""
                for dec in children["decode"]:

                    if len(condition_string):
                        condition_string += " && "

                    condition_string += arm_helpers.createMaskCondition(
                                                dec["name"], 
                                                dec["mask"], 
                                                dec["equal"]
                                            )

                print( "    " * (level) + already_has_condition +"if(" + condition_string + ")", file=ofile)
                print( "    " * (level + 1) + fallback_name, file=ofile)

                already_has_condition = "else "
        
    print("    " * (level) + "return DECODE_ERROR;", file=ofile)

    return (classes_list, decoder_list)


def printDecodeTree(ofile, full_defination):
    
    index = full_defination["index"]

    print("static uint32_t decode_encodeindex_" + index["groups"]["groupname"] + "(struct arm_decode_context* context) { // ARCH:", index["groups"]["groupname"], file=ofile)
    print("", file=ofile)

    for op in index["groups_op_list"]:
        print("    uint32_t", op, "= 0;", file=ofile)

    (classes_list, decoder_list) = printGroupTree(ofile, index["classes"], 1, index["groups"])
    #classes_list = sorted(set(classes_list))
    #decoder_list = sorted(set(decoder_list))

    print("}", file=ofile)