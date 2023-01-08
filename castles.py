import dendropy
import argparse
import re
import numpy as np

def average_terminal_bl(gts, taxon_label):
    sum_bl = 0
    for gt in gts:
        sum_bl += gt.find_node_with_taxon_label(taxon_label).edge.length
    return sum_bl/len(gts)

def process_node_annotation(annot_str):
    annotations = list(filter(None, re.split(r'[,{}:]', str(annot_str))))
    label_dict = dict()
    label_dict['support'] = float(annotations[1])
    label_dict['length'] = float(annotations[3])
    label_dict['LR_SO'] = dict()
    label_dict['LR_SO']['quartetCnt'] = float(annotations[6])
    label_dict['LR_SO']['sumInternal'] = float(annotations[8])
    label_dict['LR_SO']['sumL'] = float(annotations[10])
    label_dict['LR_SO']['sumR'] = float(annotations[12])
    label_dict['LR_SO']['sumS'] = float(annotations[14])
    label_dict['LR_SO']['sumO'] = float(annotations[16])
    label_dict['LS_RO'] = dict()
    label_dict['LS_RO']['quartetCnt'] = float(annotations[19])
    label_dict['LS_RO']['sumInternal'] = float(annotations[21])
    label_dict['LS_RO']['sumL'] = float(annotations[23])
    label_dict['LS_RO']['sumR'] = float(annotations[25])
    label_dict['LS_RO']['sumS'] = float(annotations[27])
    label_dict['LS_RO']['sumO'] = float(annotations[29])
    label_dict['LO_RS'] = dict()
    label_dict['LO_RS']['quartetCnt'] = float(annotations[32])
    label_dict['LO_RS']['sumInternal'] = float(annotations[34])
    label_dict['LO_RS']['sumL'] = float(annotations[36])
    label_dict['LO_RS']['sumR'] = float(annotations[38])
    label_dict['LO_RS']['sumS'] = float(annotations[40])
    label_dict['LO_RS']['sumO'] = float(annotations[42])
    return label_dict

def safe_div(n, d):
    return n / d if d else 0


def set_branch_length(edge, length):
    edge.length = length # if length > 0 else 10 ** (-6)
    return edge

def castles(args):
    tns = dendropy.TaxonNamespace()
    st = dendropy.Tree.get(path=args.speciestree, schema='newick', taxon_namespace=tns)
    gts = dendropy.TreeList.get(path=args.genetrees, schema='newick', taxon_namespace=tns)

    for node in st.postorder_node_iter():
        if node.taxon is not None:
            print('terminal')
            continue
        else:
            label_dict = process_node_annotation(node.label)
            num_m_gts = label_dict['LR_SO']['quartetCnt']
            num_n_gts = label_dict['LS_RO']['quartetCnt'] + label_dict['LO_RS']['quartetCnt']
            p_est = (num_m_gts - 0.5 * (1 + num_n_gts)) / (num_n_gts + num_m_gts + 1)
            d_est = -np.log(1 - p_est)

            left = node._child_nodes[0]
            right = node._child_nodes[1]
            sibling = None
            if node.parent_node is not None:
                if node.parent_node._child_nodes[0] == node:
                    sibling = node.parent_node._child_nodes[1]
                if node.parent_node._child_nodes[1] == node:
                    sibling = node.parent_node._child_nodes[0]
            else:
                node.label = None
                continue

            lm_i = safe_div(label_dict['LR_SO']['sumInternal'], label_dict['LR_SO']['quartetCnt'])
            ln_i = safe_div(label_dict['LS_RO']['sumInternal']+label_dict['LO_RS']['sumInternal'],
                            label_dict['LS_RO']['quartetCnt']+ label_dict['LO_RS']['quartetCnt'])
            lm_a = safe_div(label_dict['LR_SO']['sumL'], label_dict['LR_SO']['quartetCnt'])
            ln_a = safe_div(label_dict['LS_RO']['sumL']+label_dict['LO_RS']['sumL'],
                            label_dict['LS_RO']['quartetCnt']+label_dict['LO_RS']['quartetCnt'])
            lm_b = safe_div(label_dict['LR_SO']['sumR'], label_dict['LR_SO']['quartetCnt'])
            ln_b = safe_div(label_dict['LS_RO']['sumR']+label_dict['LO_RS']['sumR'],
                            label_dict['LS_RO']['quartetCnt']+label_dict['LO_RS']['quartetCnt'])
            lm_c = safe_div(label_dict['LR_SO']['sumS'], label_dict['LR_SO']['quartetCnt'])
            ln_c = safe_div(label_dict['LS_RO']['sumS']+label_dict['LO_RS']['sumS'],
                            label_dict['LS_RO']['quartetCnt']+label_dict['LO_RS']['quartetCnt'])
            lm_d = safe_div(label_dict['LR_SO']['sumO'], label_dict['LR_SO']['quartetCnt'])
            ln_d = safe_div(label_dict['LS_RO']['sumO']+label_dict['LO_RS']['sumO'],
                            label_dict['LS_RO']['quartetCnt']+label_dict['LO_RS']['quartetCnt'])
            l_est = 1 / 3 * (lm_i - ln_i) * d_est * (1 + 2 * p_est) / (d_est - p_est)

            print('average length non-matching', ln_i)
            l_naive = d_est * ln_i

            threshold = np.log(len(gts))
            w_formula, w_naive = threshold * d_est, 1 / (threshold * d_est)
            l_mixed = (w_formula * l_est + w_naive * l_naive) / (w_formula + w_naive)

            print("internal, d_est, p_est", d_est, p_est)
            print("l_est, l_naive, mixed", l_est, l_naive, l_mixed)

            l_est = l_mixed

            # cherry equations
            mu2_est_a = -2 * (1 + 2 * p_est) * ((lm_i - ln_i) + (lm_a - ln_a)) / (1 + 4 * p_est)
            mu2_est_b = -2 * (1 + 2 * p_est) * ((lm_i - ln_i) + (lm_b - ln_b)) / (1 + 4 * p_est)

            l_a_est = ln_a - 5 / 6 * mu2_est_a - l_est
            l_b_est = ln_b - 5 / 6 * mu2_est_b - l_est

            l_c_est = ln_c - 1 / 3 * (2 - 1 / (p_est + 1)) * (lm_c - ln_c)
            l_d_est = ln_d - 2 / 3 * (2 + 1 / p_est) * (lm_d - ln_d)

            if node.parent_node.parent_node is None: # node is child of the root
                if sibling.is_leaf():
                    if l_d_est == 0:
                        l_d_est = average_terminal_bl(gts, sibling.taxon.label)
                    set_branch_length(node.edge, l_d_est)
                else:
                    set_branch_length(node.edge, np.abs(l_est))
            elif not node.edge.length:
                set_branch_length(node.edge, np.abs(l_est))

            if left.is_leaf() and not left.edge.length:
                print(left.taxon.label)
                set_branch_length(left.edge, np.abs(l_a_est))
            if right.is_leaf() and not right.edge.length:
                print(right.taxon.label)
                set_branch_length(right.edge, np.abs(l_b_est))
            if sibling and sibling.is_leaf() and not sibling.edge.length:
                print(sibling.taxon.label)
                set_branch_length(sibling.edge, np.abs(l_c_est))
        node.label = None

    st.deroot()
    with open(args.outputtree, 'w') as f:
        f.write(str(st) + ';\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CASTLES")
    parser.add_argument("-t", "--speciestree", type=str,  required=True,
                        help="Annotated species tree file in newick format")
    parser.add_argument("-g", "--genetrees", type=str, required=True,
                        help="Gene trees file in newick format")
    parser.add_argument("-o", "--outputtree", type=str, required=True,
                        help="Species tree with SU branches in newick format")
    castles(parser.parse_args())