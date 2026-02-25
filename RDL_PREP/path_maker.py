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

        current_reg = []
        inst_tuple = []
        inst_tuple_1 = []
        hdl_name = []
        reg_has_hdl = False

        if has_register(curr_file):
            reg_pattern = re.compile(r'^\s*reg\s+(\w+)')
            hdl_pattern = re.compile(r'hdl_path\s*=\s*\{.*"([\w.]+)"\s*\}')
            instance_pattern = re.compile(r"^(?:\w+\s+)?(\w+)\s+(\w+)\s*@")

            final_defines = []

            with open(curr_file, "r") as f:
                for line in f:
                    clean_line = line.split("//")[0].strip()

                    reg_match = reg_pattern.match(clean_line)
                    if reg_match:
                        current_reg.append(reg_match.group(1))
                        reg_has_hdl = False
                        continue

                    if current_reg:
                        hdl_match = hdl_pattern.search(clean_line)
                        if hdl_match:
                            reg_has_hdl = True
                            hdl_name.append(hdl_match.group(1))
                            continue

                    if reg_has_hdl:
                        inst_match = instance_pattern.match(clean_line)
                        if inst_match:
                            inst_tuple.append(inst_match.group(1))
                            inst_tuple_1.append(inst_match.group(2))
                            if(inst_tuple.pop(0) == current_reg.pop(0)):
                                final_defines.append((inst_tuple_1.pop(0), f"{curr_path}.{hdl_name.pop(0)}"))
                                
                                
        else:
            children = extract_sub_instances(curr_file)
            for comp_type, inst_name in children:
                if comp_type in comp_to_path:
                    child_file = comp_to_path[comp_type]
                    queue.append((child_file, f"{curr_path}.{inst_name}"))
                    print(f"{queue}")

    output_file = ROOT_DIR + "/" + OUT_FILE
    pattern_y = re.compile(r"(\w+)\.add_hdl_path_slice")

    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            lines = f.readlines()

    for reg_name, full_path in final_defines:
        replaced = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{reg_name}.add_hdl_path_slice"):
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