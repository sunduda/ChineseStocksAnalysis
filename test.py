l = 33
a = [3, 6, 19, 22, 26]
b = []
i = [0, 0, 0, 0, 0]
for i[0] in (-1, 1):
    for i[1] in (-1, 1):
        for i[2] in (-1, 1):
            for i[3] in (-1, 1):
                for i[4] in (-1, 1):
                    b.append([i[0], i[1], i[2], i[3], i[4]])
maxn=0
for k in range(len(b)):
    v = b[k].copy()
    pos = a.copy()
    n = 0
    while(pos):
        n = n + 1
        for j in range(len(pos)-1):
            if (v[j] > v[j+1]) and (pos[j+1] - pos[j]<=1):
                v[j] = -v[j]
                v[j+1] = -v[j+1]
                if pos[j+1] - pos[j]>0.4:
                    pos[j], pos[j+1] = pos[j+1], pos[j]
        for j in reversed(range(len(pos))):
            pos[j] = pos[j] + v[j]
            if (pos[j]<=0) or (pos[j]>=l):
                del pos[j]
                del v[j]
    if maxn < n:
        maxn = n
print(maxn)
    
