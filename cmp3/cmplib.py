from part import PartitionedList

def cmp3(a, r, b):
    #
    # produces 2 lists:
    #
    #       D = R-A-B = (R-A)-B
    #       M = A*B-R = (A-R)*B
    #
    a_r = set(a)    # this will be A-R
    r_a = set()     # this will be R-A
    for x in r:
            try:    a_r.remove(x)
            except KeyError:
                    r_a.add(x)
    d = r_a
    m = set()
    for x in b:
            try:    d.remove(x)
            except KeyError:    pass
            if x in a_r:
                    m.add(x)
    #print("memory utilization at the end of cmp3, MB:", getMemory())
    return list(d), list(m)

def lines(f):
    l = f.readline()
    while l:
        yield l
        l = f.readline()

def cmp3_lists(a_list, r_list, b_list):

    assert a_list.NParts == r_list.NParts and r_list.NParts == b_list.NParts, "Inconsistent number of parts: B:%d, R:%d, A:%d" % (
        b_list.NParts, r_list.NParts, a_list.NParts)

    d_list, m_list = [], []
    for i, (af, rf, bf) in enumerate(zip(a_list.files(), r_list.files(), b_list.files())):
            #print("Comparing %s %s %s..." % (an, rn, bn))
            d, m = cmp3(lines(af), lines(rf), lines(bf))
            d_list += d
            m_list += m
            print("Partition %d compared: dark:%d missing:%d" % (i, len(d), len(m))) 
    return d_list, m_list

def cmp3_generator(a_list, r_list, b_list):

    assert a_list.NParts == r_list.NParts and r_list.NParts == b_list.NParts, "Inconsistent number of parts: B:%d, R:%d, A:%d" % (
        b_list.NParts, r_list.NParts, a_list.NParts)

    d_list, m_list = [], []
    for i, (af, rf, bf) in enumerate(zip(a_list.files(), r_list.files(), b_list.files())):
            #print("Comparing %s %s %s..." % (an, rn, bn))
            d, m = cmp3(lines(af), lines(rf), lines(bf))
            for f in d:
                yield ('d', f)
            for f in m:
                yield ('m', f)

def cmp3_parts(a_prefix, r_prefix, b_prefix):
    a_list = PartitionedList.open(a_prefix)
    r_list = PartitionedList.open(r_prefix)
    b_list = PartitionedList.open(b_prefix)
    return cmp3_lists(a_list, r_list, b_list)
