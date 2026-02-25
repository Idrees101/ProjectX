import os
import sys
import re

ROOT_DIR = "/home/zeeshan/RDL/RDL_PREP"
TOP_NAME = "tb_top"
OUT_FILE = "uvm_reg_model.svh"

# ==========================================================
# Function for building the paths and storing them in index
# ==========================================================
def build_component_index(root):
    index = {}
    pattern = re.compile(r"\b(addrmap|regfile)\s+(\w+)\b")

    for base, dirs, files in os.walk(root, topdown=True):
        for f in files:
            if f.lower().endswith(".rdl"):
                path = os.path.join(base, f)
                print(f"Searching in : {path}")
                try:
                    with open(path, "r") as file_content:
                        content = file_content.read()
                        match = pattern.findall(content)
                        for _, comp_path in match:
                            index[comp_path] = path
                            print(f"{comp_path}")
                except:
                    continue
    return index

# =====================================
# Function to extract name and Instance
# =====================================
def extract_sub_instances(rdl_file):
    pattern = re.compile(r"^\s*(\w+)\s+#\(\.ext_hdl_path\(\s*\"([^\"]+)\"\)\)\s+(\w+)\s+(@|;)")
    found = []
    with open(rdl_file, "r") as file:
        for line in file:
            clean_line = line.split("//")[0].strip()
            m = pattern.search(clean_line)
            if m:
                found.append((m.group(1), m.group(2))) 
        
    print(f"{found}")
    return found

# ==================================
# Function to check it has registers
# ==================================
def has_register(rdl_file):
    try:
        with open(rdl_file, "r") as f:
            content = f.read()
            return "reg " in content or "field " in content
    except:
        return False

# =============================
# Main Phase 
# =============================
def main():
   
    comp_to_path = build_component_index(ROOT_DIR)
    
    queue = [(sys.argv[1], TOP_NAME)]
    final_defines = []
    instance_name = []
    visited_path = set()

    while queue:
        curr_file, curr_path = queue.pop(0)

        if curr_path in visited_path:
            continue
        visited_path.add(curr_path)

        if has_register(curr_file):
            reg_pattern = re.compile(r'^\s*reg\s+(\w+)')
            hdl_pattern = re.compile(r'hdl_path\s*=\s*\{.*"([\w.]+)"\s*\}')
            instance_pattern = re.compile(r"^(?:\w+\s+)?(\w+)\s+(\w+)(?:\[(\d+)\])?\s+@")

            reg_to_hdl = {}
            reg_to_inst = {}
            current_reg = None

            with open(curr_file, "r") as f:
                for line in f:
                    clean_line = line.split("//")[0].strip()
                    reg_match = reg_pattern.match(clean_line)
                    if reg_match:
                        current_reg = reg_match.group(1)
                        continue

                    if current_reg:
                        hdl_match = hdl_pattern.search(clean_line)
                        if hdl_match:
                            reg_to_hdl[current_reg] = hdl_match.group(1)
                            continue

                    inst_match = instance_pattern.match(clean_line)
                    if inst_match:
                        reg_type = inst_match.group(1)
                        inst_name = inst_match.group(2)
                        reg_to_inst[reg_type] = inst_name

            for reg_name in reg_to_hdl:
                if reg_name in reg_to_inst:
                    full_path = f"{curr_path}.{reg_to_hdl[reg_name]}"
                    final_defines.append((reg_to_inst[reg_name], full_path))
                                
        else:
            children = extract_sub_instances(curr_file)
            for comp_type, inst_name in children:
                if comp_type in comp_to_path:
                    child_file = comp_to_path[comp_type]
                    queue.append((child_file, f"{curr_path}.{inst_name}"))
                    print(f"{queue}")

    output_file = ROOT_DIR + "/" + OUT_FILE
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            lines = f.readlines()

    for reg_name, full_path in final_defines:
        replaced = False
        search_pattern = re.compile(rf"\b{reg_name}\s*(\[[^\]]+\])?\.add_hdl_path_slice\b")
        print(f"DEBUG: Searching for pattern: {search_pattern.pattern}")
        for i, line in enumerate(lines):
            match = search_pattern.search(line)
            if match:
                print(f"{match}")
                array_part = match.group(1)
                print(f"{array_part}")
                if array_part is not None:
                    lines[i] = f'                {reg_name}[i0].add_hdl_path_slice("{full_path}", -1, -1)\n'
                    replaced = True
                    break
                else:
                    lines[i] = f'            {reg_name}.add_hdl_path_slice("{full_path}", -1, -1)\n'
                    replaced = True
                    break

        if not replaced:
            lines.append(f'{reg_name}.add_hdl_path_slice("{full_path}", -1, -1)\n')

    with open(output_file, "w") as out:
        out.writelines(lines)

    print(f"--- Success! Generated {len(final_defines)} defines in {OUT_FILE} ---")

if __name__ == "__main__":
    main()