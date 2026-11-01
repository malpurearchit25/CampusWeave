"""Executable teaching models. These simulations are not a distributed DBMS or Hadoop cluster."""
from itertools import permutations,combinations
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor

def closure(attributes,fds):
    result=set(attributes)
    while True:
        previous=result.copy()
        for left,right in fds:
            if set(left)<=result:result.update(right)
        if result==previous:return result

def minimal_cover(fds):
    cover=[(frozenset(left),frozenset([a])) for left,right in fds for a in sorted(right)]
    cover=list(dict.fromkeys(cover))
    for i,(left,right) in enumerate(cover):
        for a in sorted(left):
            reduced=left-{a}
            if right<=closure(reduced,cover):left=frozenset(reduced);cover[i]=(left,right)
    for fd in cover.copy():
        reduced=cover.copy();reduced.remove(fd)
        if fd[1]<=closure(fd[0],reduced):cover.remove(fd)
    return cover

def candidate_keys(attributes,fds):
    attrs=sorted(attributes);keys=[]
    for size in range(1,len(attrs)+1):
        for choice in combinations(attrs,size):
            key=set(choice)
            if not any(k<=key for k in keys) and closure(key,fds)>=set(attrs):keys.append(key)
    return keys

def synthesize_3nf(attributes,fds):
    cover=minimal_cover(fds);groups=defaultdict(set)
    for left,right in cover:groups[left].update(right)
    relations=[set(left)|right for left,right in groups.items()]
    relations=[r for r in relations if not any(r<other for other in relations)]
    keys=candidate_keys(attributes,fds)
    if not any(key<=r for key in keys for r in relations):relations.append(keys[0])
    return relations

def conflict_graph(schedule):
    edges=set();transactions={t for t,op,item in schedule}
    for i,(t,op,item) in enumerate(schedule):
        for u,other,target in schedule[i+1:]:
            if t!=u and item==target and 'W' in (op,other):edges.add((t,u))
    order=[];remaining=set(transactions)
    while remaining:
        ready=sorted(t for t in remaining if not any(b==t and a in remaining for a,b in edges))
        if not ready:return sorted(edges),False,[]
        order.extend(ready);remaining-=set(ready)
    return sorted(edges),True,order

def view_signature(schedule):
    last={};reads=[];read_numbers=Counter();write_numbers=Counter()
    for t,op,item in schedule:
        if op=='R':
            read_numbers[t]+=1;reads.append(((t,read_numbers[t],item),last.get(item,'INITIAL')))
        else:
            write_numbers[t]+=1
            last[item]=(t,write_numbers[t])
    return sorted(reads),sorted(last.items())

def view_serial_order(schedule):
    transactions=sorted({t for t,_,_ in schedule});target=view_signature(schedule)
    if len(transactions)>6:raise ValueError('Teaching model supports at most six transactions.')
    for order in permutations(transactions):
        serial=[step for t in order for step in schedule if step[0]==t]
        if view_signature(serial)==target:return list(order)
    return None

def recovery_demo():
    initial={'room_capacity':60,'faculty_limit':16}
    log=[('T1','room_capacity',60,65),('T2','faculty_limit',16,20)]
    committed={'T1'};disk={'room_capacity':60,'faculty_limit':20}
    for t,key,old,new in reversed(log):
        if t not in committed:disk[key]=old
    for t,key,old,new in log:
        if t in committed:disk[key]=new
    return {'initial':initial,'write_ahead_log':log,'committed':sorted(committed),'after_crash_recovery':disk,'model':'Simplified undo/redo teaching model; not an implementation of InnoDB recovery.'}

def run_theory_experiments():
    fds=[({'A'},{'B'}),({'B'},{'C'}),({'A'},{'C'}),({'A','B'},{'D'})]
    cover=minimal_cover(fds);relations=synthesize_3nf(set('ABCD'),fds)
    assert closure({'A'},fds)==set('ABCD')
    assert {(''.join(sorted(l)),''.join(sorted(r))) for l,r in cover}=={('A','B'),('B','C'),('A','D')}
    serial=[('T1','R','X'),('T1','W','X'),('T2','R','X'),('T2','W','X')]
    cyclic=[('T1','R','X'),('T2','R','Y'),('T1','W','Y'),('T2','W','X')]
    blind=[('T1','W','X'),('T2','W','X'),('T1','W','X')]
    assert conflict_graph(serial)[1] and not conflict_graph(cyclic)[1]
    assert not conflict_graph(blind)[1] and view_serial_order(blind)==['T2','T1']
    rows=[{'id':i,'department':'Computer' if i%2 else 'Electronics','hours':1+i%3} for i in range(1,25)]
    fragments={department:[r for r in rows if r['department']==department] for department in ['Computer','Electronics']}
    reconstructed=sorted([r for fragment in fragments.values() for r in fragment],key=lambda r:r['id'])
    assert reconstructed==rows
    vertical_identity=[{k:r[k] for k in ['id','department']} for r in rows]
    vertical_hours={r['id']:r['hours'] for r in rows}
    assert [{**r,'hours':vertical_hours[r['id']]} for r in vertical_identity]==rows
    def mapper(fragment):
        totals=Counter()
        for r in fragment:totals[r['department']]+=r['hours']
        return totals
    with ThreadPoolExecutor(max_workers=2) as pool:partials=list(pool.map(mapper,fragments.values()))
    reduced=sum(partials,Counter());assert reduced==mapper(rows)
    # Independent preference MVDs must produce the full cross product.
    preference=[('F1',day,room) for day in ['MON','TUE'] for room in ['LAB1','LAB2']]
    decomposed_days={r[:2] for r in preference};decomposed_rooms={(r[0],r[2]) for r in preference}
    assert {(f,d,r) for f,d in decomposed_days for g,r in decomposed_rooms if f==g}==set(preference)
    return {'fd_closure_A':sorted(closure({'A'},fds)),'minimal_cover':[[sorted(l),sorted(r)] for l,r in cover],
      'candidate_keys':[sorted(k) for k in candidate_keys(set('ABCD'),fds)],'synthesis_3nf':[sorted(r) for r in relations],
      'conflict_serializable':{'edges':conflict_graph(serial)[0],'order':conflict_graph(serial)[2]},
      'cyclic_schedule':{'edges':conflict_graph(cyclic)[0],'serializable':False},
      'view_not_conflict_serializable':{'schedule':blind,'view_equivalent_serial_order':view_serial_order(blind)},
      'recovery':recovery_demo(),'horizontal_fragment_counts':{k:len(v) for k,v in fragments.items()},
      'vertical_reconstruction':True,'parallel_mapreduce_totals':dict(reduced),'parallel_matches_serial':True,
      'fourth_normal_form':{'cross_product_rows':len(preference),'day_projection':len(decomposed_days),'room_projection':len(decomposed_rooms),'lossless':True},
      'cap_partition_demo':{'initial_replicas':[1,1],'partitioned_write_on_A':2,'AP_read_on_B':1,'CP_read_on_B':'rejected until quorum reachable','after_reconciliation':[2,2]},
      'hdfs_replica_model':{'blocks':{'B1':['N1','N2','N3'],'B2':['N2','N3','N1']},'failed_node':'N1','remaining_replicas_per_block':2},
      'scope':'Executed local algorithms and simulations, not a multi-machine database or Hadoop deployment.'}
