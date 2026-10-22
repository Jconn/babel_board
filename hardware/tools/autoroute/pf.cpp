// Negotiated-congestion (PathFinder) grid router, F.Cu/B.Cu with through vias.
// Proposes routes only; pcbnew re-checks every segment and via exactly.
//
// usage: pf grid.bin names.json out.json [iters]
// env: CLR (0.17), PF0 (0.5), PFMUL (1.6), HFAC (0.4), SEED (0)
#include <bits/stdc++.h>
using namespace std;

static int NX, NY, N;
static double G, CLR, QE;
static const double VIA_R = 0.3, VIA_COST_MM = 2.0, TURN = 0.3;
static double PARTNER_HALF = 0.1, QD = 0.02;   // widest dynamic partner / segment slack
static vector<int32_t> lab[3];
static vector<uint8_t> viaforbid;

struct Net {
    string name; int id; double w;
    vector<vector<int>> cl;            // cluster cells (l*N + c)
    vector<uint8_t> blk[2], blkv;      // fixed-copper blocking
    vector<vector<int>> paths;         // each path: sequence of l*N + c
    vector<int> st[3];                 // stamped cells in fields T0, T1, VQ
    bool complete = false;
    int span = 0;
};
static vector<Net> nets;

// ---------------------------------------------------------------- EDT
static void edt1(const float* f, int n, float* d, int* v, float* z) {
    int k = 0; v[0] = 0; z[0] = -1e20f; z[1] = 1e20f;
    for (int q = 1; q < n; q++) {
        float s;
        while (true) {
            s = ((f[q] + (float)q * q) - (f[v[k]] + (float)v[k] * v[k])) / (2.0f * q - 2.0f * v[k]);
            if (s <= z[k]) { k--; if (k < 0) { k = 0; break; } } else break;
        }
        k++; v[k] = q; z[k] = s; z[k + 1] = 1e20f;
    }
    k = 0;
    for (int q = 0; q < n; q++) {
        while (z[k + 1] < q) k++;
        d[q] = (float)(q - v[k]) * (q - v[k]) + f[v[k]];
    }
}
// squared distance (cells) to nearest true cell
static vector<float> edt(const vector<uint8_t>& m) {
    const float INF = 1e12f;
    vector<float> D(N);
    int mx = max(NX, NY);
    vector<float> f(mx), d(mx), z(mx + 1); vector<int> v(mx);
    for (int i = 0; i < NX; i++) {
        for (int j = 0; j < NY; j++) f[j] = m[j * NX + i] ? 0 : INF;
        edt1(f.data(), NY, d.data(), v.data(), z.data());
        for (int j = 0; j < NY; j++) D[j * NX + i] = d[j];
    }
    for (int j = 0; j < NY; j++) {
        for (int i = 0; i < NX; i++) f[i] = D[j * NX + i];
        edt1(f.data(), NX, d.data(), v.data(), z.data());
        for (int i = 0; i < NX; i++) D[j * NX + i] = d[i];
    }
    return D;
}

// ---------------------------------------------------------------- fields
static vector<int16_t> fld[3];     // 0: T on F, 1: T on B, 2: VQ (via placement)
static vector<float> hist[3];
static vector<int> stampv[3]; static int stampgen = 0;
static vector<pair<int,int>> disk_cells(double r) {
    vector<pair<int,int>> o; int R = (int)ceil(r / G);
    for (int dj = -R; dj <= R; dj++) for (int di = -R; di <= R; di++)
        if (hypot(di, dj) * G <= r) o.push_back({dj, di});
    return o;
}
static void stamp_disk(int f, int c, const vector<pair<int,int>>& dk, vector<int>& out) {
    int j = c / NX, i = c % NX;
    for (auto [dj, di] : dk) {
        int jj = j + dj, ii = i + di;
        if (jj < 0 || jj >= NY || ii < 0 || ii >= NX) continue;
        int cc = jj * NX + ii;
        if (stampv[f][cc] == stampgen) continue;
        stampv[f][cc] = stampgen; out.push_back(cc);
    }
}
static void add_net(Net& n) {
    double rT = n.w / 2 + PARTNER_HALF + CLR + QD;           // my track vs other tracks
    double rVT = VIA_R + PARTNER_HALF + CLR + QD;            // my via vs other tracks
    double rTV = VIA_R + n.w / 2 + CLR + QD;                 // my track vs other vias
    double rVV = 0.8;                                        // via vs via (hole-to-hole)
    auto dT = disk_cells(rT), dVT = disk_cells(rVT), dTV = disk_cells(rTV), dVV = disk_cells(rVV);
    for (int f = 0; f < 3; f++) n.st[f].clear();
    stampgen++;
    for (auto& p : n.paths) {
        for (size_t k = 0; k < p.size(); k++) {
            int l = p[k] / N, c = p[k] % N;
            stamp_disk(l, c, dT, n.st[l]);
            stamp_disk(2, c, dTV, n.st[2]);
            if (k + 1 < p.size() && p[k + 1] / N != l) {      // via here
                stamp_disk(0, c, dVT, n.st[0]);
                stamp_disk(1, c, dVT, n.st[1]);
                stamp_disk(2, c, dVV, n.st[2]);
            }
        }
    }
    for (int f = 0; f < 3; f++) for (int c : n.st[f]) fld[f][c]++;
}
static void rip_net(Net& n) {
    for (int f = 0; f < 3; f++) { for (int c : n.st[f]) fld[f][c]--; n.st[f].clear(); }
    n.paths.clear(); n.complete = false;
}
// conflicts of a routed net (cells where another net's claim overlaps)
static int conflicts(const Net& n, bool addhist, double hfac) {
    int cnt = 0;
    for (auto& p : n.paths) for (size_t k = 0; k < p.size(); k++) {
        int l = p[k] / N, c = p[k] % N;
        if (fld[l][c] > 1) { cnt++; if (addhist) hist[l][c] += hfac; }
        if (k + 1 < p.size() && p[k + 1] / N != l && fld[2][c] > 1) { cnt++; if (addhist) hist[2][c] += hfac; }
    }
    return cnt;
}

// ---------------------------------------------------------------- A*
static const int DJ[8] = {0, 0, 1, -1, 1, 1, -1, -1}, DI[8] = {1, -1, 0, 0, 1, -1, 1, -1};
static const double DC[8] = {1, 1, 1, 1, M_SQRT2, M_SQRT2, M_SQRT2, M_SQRT2};
static vector<double> gsc; static vector<int32_t> prv; static vector<int> touched;
static vector<uint8_t> isT, isS;   // per l*N+c target / own-pass
static double PF = 0.5;
static bool STRICT = false;   // final phase: other nets' claims are hard obstacles

// state = ((l*N)+c)*9 + d
static bool astar(Net& n, const vector<int>& src, const vector<int>& dst, int j0, int j1, int i0, int i1, vector<int>& path) {
    int tj0 = INT_MAX, tj1 = INT_MIN, ti0 = INT_MAX, ti1 = INT_MIN;
    for (int s : dst) { int c = s % N, j = c / NX, i = c % NX; tj0 = min(tj0, j); tj1 = max(tj1, j); ti0 = min(ti0, i); ti1 = max(ti1, i); }
    auto h = [&](int j, int i) {
        int dj = max({tj0 - j, 0, j - tj1}), di = max({ti0 - i, 0, i - ti1});
        int a = min(dj, di), b = max(dj, di);
        return (double)(b - a) + a * M_SQRT2;
    };
    for (int s : touched) { gsc[s] = 1e30f; prv[s] = -1; }
    touched.clear();
    typedef pair<double, int> E;
    priority_queue<E, vector<E>, greater<E>> pq;
    for (int s : src) {
        int l = s / N, c = s % N, j = c / NX, i = c % NX;
        if (j < j0 || j >= j1 || i < i0 || i >= i1) continue;
        int st = s * 9 + 8;
        gsc[st] = 0; prv[st] = -1; touched.push_back(st);
        pq.push({h(j, i), st});
    }
    double viac = VIA_COST_MM / G;
    long exp = 0, maxexp = getenv("MAXEXP") ? atol(getenv("MAXEXP")) : 8000000;
    while (!pq.empty()) {
        auto [f, st] = pq.top(); pq.pop();
        int lc = st / 9, d = st % 9, l = lc / N, c = lc % N, j = c / NX, i = c % NX;
        double g = gsc[st];
        if (f - h(j, i) > g + 1e-6) continue;
        if (isT[lc] && !isS[lc]) {
            path.clear();
            int s = st;
            while (s >= 0) { int x = s / 9; if (path.empty() || path.back() != x) path.push_back(x); s = prv[s]; }
            reverse(path.begin(), path.end());
            return true;
        }
        if (++exp > maxexp) { if (getenv("VERBOSE")) fprintf(stderr, "    cap hit\n"); return false; }
        for (int k = 0; k < 8; k++) {
            int nj = j + DJ[k], ni = i + DI[k];
            if (nj < j0 || nj >= j1 || ni < i0 || ni >= i1) continue;
            int nc = nj * NX + ni, nlc = l * N + nc;
            bool free_ = isT[nlc] || isS[nlc];
            if (n.blk[l][nc] && !free_) continue;
            if (STRICT && fld[l][nc] > 0 && !free_) continue;
            if (k >= 4) {
                int a = l * N + j * NX + ni, b = l * N + nj * NX + i;
                if ((n.blk[l][j * NX + ni] && !isT[a] && !isS[a]) || (n.blk[l][nj * NX + i] && !isT[b] && !isS[b])) continue;
            }
            double cost = DC[k] * (1 + hist[l][nc]) * (1 + PF * fld[l][nc]);
            if (d != 8 && d != k) cost += TURN;
            int ns = nlc * 9 + k;
            double ng = g + cost;
            if (ng < gsc[ns]) {
                if (gsc[ns] > 1e29f) touched.push_back(ns);
                gsc[ns] = ng; prv[ns] = st; pq.push({ng + h(nj, ni), ns});
            }
        }
        // via
        if (!n.blkv[c] && !(STRICT && fld[2][c] > 0)) {
            int ol = 1 - l, nlc = ol * N + c;
            if (!n.blk[ol][c] || isT[nlc] || isS[nlc]) {
                double cost = viac * (1 + hist[2][c]) * (1 + PF * fld[2][c]);
                int ns = nlc * 9 + 8;
                double ng = g + cost;
                if (ng < gsc[ns]) {
                    if (gsc[ns] > 1e29f) touched.push_back(ns);
                    gsc[ns] = ng; prv[ns] = st; pq.push({ng + h(j, i), ns});
                }
            }
        }
    }
    if (getenv("VERBOSE")) fprintf(stderr, "    exhausted after %ld\n", exp);
    return false;
}

static bool route_net(Net& n) {
    n.paths.clear();
    vector<int> tree = n.cl[0];
    vector<int> rest; for (size_t k = 1; k < n.cl.size(); k++) rest.push_back(k);
    vector<int> owncells;
    for (auto& cl : n.cl) for (int s : cl) { isS[s] = 1; owncells.push_back(s); }
    bool ok = true;
    while (!rest.empty()) {
        vector<int> dst;
        for (int k : rest) for (int s : n.cl[k]) { dst.push_back(s); }
        for (int s : dst) isT[s] = 1;
        for (int s : dst) isS[s] = 0;
        int j0 = INT_MAX, j1 = INT_MIN, i0 = INT_MAX, i1 = INT_MIN;
        for (auto* v : {&tree, &dst}) for (int s : *v) { int c = s % N; j0 = min(j0, c / NX); j1 = max(j1, c / NX); i0 = min(i0, c % NX); i1 = max(i1, c % NX); }
        vector<int> path; bool found = false;
        for (double m : {4.0, 10.0, 1000.0}) {
            int M = (int)(m / G);
            if (astar(n, tree, dst, max(j0 - M, 0), min(j1 + M + 1, NY), max(i0 - M, 0), min(i1 + M + 1, NX), path)) { found = true; break; }
        }
        for (int s : dst) { isT[s] = 0; isS[s] = 1; }
        if (!found) { ok = false; break; }
        int end = path.back(), hit = -1;
        for (int k : rest) { for (int s : n.cl[k]) if (s == end) { hit = k; break; } if (hit >= 0) break; }
        rest.erase(find(rest.begin(), rest.end(), hit));
        for (int s : n.cl[hit]) tree.push_back(s);
        for (int s : path) tree.push_back(s);
        n.paths.push_back(path);
    }
    for (int s : owncells) isS[s] = 0;
    n.complete = ok;
    return ok;
}

// ---------------------------------------------------------------- output
static string geom_json(const vector<int>& p) {
    // split by layer, merge collinear runs
    string tr = "[", vi = "[";
    auto pt = [&](int c) { char b[64]; snprintf(b, 64, "[%.4f,%.4f]", (c % NX + 0.5) * G, (c / NX + 0.5) * G); return string(b); };
    size_t a = 0; bool firstT = true, firstV = true;
    while (a < p.size()) {
        size_t b = a; int l = p[a] / N;
        while (b + 1 < p.size() && p[b + 1] / N == l) b++;
        if (b > a) {
            vector<int> s{p[a] % N};
            for (size_t k = a + 1; k < b; k++) {
                int c0 = s.back(), c1 = p[k] % N, c2 = p[k + 1] % N;
                int d1j = c1 / NX - c0 / NX, d1i = c1 % NX - c0 % NX, d2j = c2 / NX - c1 / NX, d2i = c2 % NX - c1 % NX;
                if ((long)d1j * d2i - (long)d1i * d2j != 0 || (long)d1j * d2j + (long)d1i * d2i < 0) s.push_back(c1);
            }
            s.push_back(p[b] % N);
            if (!firstT) tr += ","; firstT = false;
            tr += string("[\"") + (l == 0 ? "F" : "B") + "\",[";
            for (size_t k = 0; k < s.size(); k++) { if (k) tr += ","; tr += pt(s[k]); }
            tr += "]]";
        }
        if (b + 1 < p.size()) { if (!firstV) vi += ","; firstV = false; vi += pt(p[b] % N); }
        a = b + 1;
    }
    return "{\"tracks\":" + tr + "],\"vias\":" + vi + "]}";
}
static void write_out(const char* fn, const vector<char>& keep) {
    FILE* f = fopen(fn, "w");
    fprintf(f, "{");
    bool first = true;
    for (size_t k = 0; k < nets.size(); k++) {
        Net& n = nets[k];
        if (!keep[k] || n.paths.empty()) continue;
        if (!first) fprintf(f, ","); first = false;
        fprintf(f, "\"%s\":{\"width\":%.3f,\"complete\":%s,\"routes\":[", n.name.c_str(), n.w, n.complete ? "true" : "false");
        for (size_t q = 0; q < n.paths.size(); q++) fprintf(f, "%s%s", q ? "," : "", geom_json(n.paths[q]).c_str());
        fprintf(f, "]}");
    }
    fprintf(f, "}\n"); fclose(f);
}

int main(int argc, char** argv) {
    CLR = getenv("CLR") ? atof(getenv("CLR")) : 0.17;
    PF = getenv("PF0") ? atof(getenv("PF0")) : 0.5;
    double PFMUL = getenv("PFMUL") ? atof(getenv("PFMUL")) : 1.6;
    double HFAC = getenv("HFAC") ? atof(getenv("HFAC")) : 0.4;
    int iters = argc > 4 ? atoi(argv[4]) : 40;
    unsigned seed = getenv("SEED") ? atoi(getenv("SEED")) : 0;
    FILE* f = fopen(argv[1], "rb");
    fread(&NX, 4, 1, f); fread(&NY, 4, 1, f); fread(&G, 8, 1, f);
    N = NX * NY; QE = G * M_SQRT2 / 2 + 0.005;
    for (int l = 0; l < 3; l++) { lab[l].resize(N); fread(lab[l].data(), 4, N, f); }
    viaforbid.resize(N); fread(viaforbid.data(), 1, N, f);
    int nn; fread(&nn, 4, 1, f);
    nets.resize(nn);
    for (auto& n : nets) {
        int ncl; fread(&n.id, 4, 1, f); fread(&n.w, 8, 1, f); fread(&ncl, 4, 1, f);
        n.cl.resize(ncl);
        for (auto& c : n.cl) { int m; fread(&m, 4, 1, f); c.resize(m); fread(c.data(), 4, m, f); }
    }
    fclose(f);
    for (const auto& n : nets) PARTNER_HALF = max(PARTNER_HALF, n.w / 2);
    {   // names
        ifstream in(argv[2]); string s((istreambuf_iterator<char>(in)), {});
        size_t p = 0; int k = 0;
        while ((p = s.find('"', p)) != string::npos) { size_t q = s.find('"', p + 1); nets[k++].name = s.substr(p + 1, q - p - 1); p = q + 1; }
    }
    // fixed-copper blocking per net
    double edge = 0.3 + 0.02;
    #pragma omp parallel for schedule(dynamic)
    for (int k = 0; k < nn; k++) {
        Net& n = nets[k];
        vector<uint8_t> any(N, 0);
        for (int l = 0; l < 3; l++) {
            vector<uint8_t> m(N);
            for (int c = 0; c < N; c++) { int v = lab[l][c]; m[c] = v != 0 && v != n.id; any[c] |= m[c]; }
            if (l == 2) break;
            auto D = edt(m);
            double r = (CLR + n.w / 2 + QE) / G, r2 = r * r, e = (edge + n.w / 2) / G;
            n.blk[l].resize(N);
            for (int c = 0; c < N; c++) {
                int j = c / NX, i = c % NX;
                n.blk[l][c] = D[c] < r2 || i + 0.5 < e || NX - i - 0.5 < e || j + 0.5 < e || NY - j - 0.5 < e;
            }
        }
        auto D = edt(any);
        double r = (CLR + VIA_R + QE) / G, r2 = r * r, e = (edge + VIA_R) / G;
        n.blkv.resize(N);
        for (int c = 0; c < N; c++) {
            int j = c / NX, i = c % NX;
            n.blkv[c] = D[c] < r2 || viaforbid[c] || i + 0.5 < e || NX - i - 0.5 < e || j + 0.5 < e || NY - j - 0.5 < e;
        }
        int j0 = INT_MAX, j1 = INT_MIN, i0 = INT_MAX, i1 = INT_MIN;
        for (auto& cl : n.cl) for (int s : cl) { int c = s % N; j0 = min(j0, c / NX); j1 = max(j1, c / NX); i0 = min(i0, c % NX); i1 = max(i1, c % NX); }
        n.span = (j1 - j0) + (i1 - i0);
    }
    fprintf(stderr, "blocking masks ready\n");
    if (getenv("DIAG")) {   // flood-fill reachability from each cluster of every net
        for (auto& n : nets) {
            fprintf(stderr, "%s:", n.name.c_str());
            for (size_t q = 0; q < n.cl.size(); q++) {
                vector<uint8_t> seen(2 * N, 0); vector<int> st;
                vector<uint8_t> own(2 * N, 0); for (auto& cl : n.cl) for (int s : cl) own[s] = 1;
                for (int s : n.cl[q]) { seen[s] = 1; st.push_back(s); }
                long cnt = 0; int j0 = 1e9, j1 = -1, i0 = 1e9, i1 = -1; set<int> reach;
                while (!st.empty()) {
                    int s = st.back(); st.pop_back(); cnt++;
                    int l = s / N, c = s % N, j = c / NX, i = c % NX;
                    j0 = min(j0, j); j1 = max(j1, j); i0 = min(i0, i); i1 = max(i1, i);
                    for (size_t r = 0; r < n.cl.size(); r++) if (r != q) for (int t : n.cl[r]) if (t == s) reach.insert(r);
                    if (cnt > 200000) break;
                    for (int k = 0; k < 4; k++) {
                        int nj = j + DJ[k], ni = i + DI[k];
                        if (nj < 0 || nj >= NY || ni < 0 || ni >= NX) continue;
                        int ns = l * N + nj * NX + ni;
                        if (seen[ns] || (n.blk[l][nj * NX + ni] && !own[ns])) continue;
                        seen[ns] = 1; st.push_back(ns);
                    }
                    if (!n.blkv[c] && !(STRICT && fld[2][c] > 0)) { int ns = (1 - l) * N + c; if (!seen[ns] && (!n.blk[1 - l][c] || own[ns])) { seen[ns] = 1; st.push_back(ns); } }
                }
                int c0 = n.cl[q].empty() ? 0 : n.cl[q][0] % N;
                fprintf(stderr, " [cl%zu @%.1f,%.1f reach %s%ld box %.1f-%.1f,%.1f-%.1f]", q, (c0 % NX + .5) * G, (c0 / NX + .5) * G,
                        cnt > 200000 ? ">" : "", cnt, i0 * G, i1 * G, j0 * G, j1 * G);
            }
            fprintf(stderr, "\n");
        }
        return 0;
    }
    for (int q = 0; q < 3; q++) { fld[q].assign(N, 0); hist[q].assign(N, 0); stampv[q].assign(N, 0); }
    gsc.assign((size_t)2 * N * 9, 1e30); prv.assign((size_t)2 * N * 9, -1);
    isT.assign(2 * N, 0); isS.assign(2 * N, 0);

    vector<int> order(nn); iota(order.begin(), order.end(), 0);
    auto byspan = [&](int a, int b) { bool wa = nets[a].w > 0.2001, wb = nets[b].w > 0.2001; return wa != wb ? wa : nets[a].span < nets[b].span; };
    sort(order.begin(), order.end(), byspan);
    mt19937 rng(seed);
    int best = INT_MAX; vector<vector<vector<int>>> bestp; vector<char> bestc;
    for (int it = 0; it < iters; it++) {
        int routed = 0;
        for (int k : order) {
            Net& n = nets[k];
            if (it > 0 && n.complete && (n.w > 0.2001 || conflicts(n, false, 0) == 0)) continue;
            if (getenv("ONLY") && n.name != getenv("ONLY")) continue;
            rip_net(n);
            auto t0 = chrono::steady_clock::now();
            route_net(n);
            add_net(n);
            if (getenv("VERBOSE")) fprintf(stderr, "  %-18s %s %zu/%zu %.2fs\n", n.name.c_str(), n.complete ? "ok  " : "FAIL", n.paths.size(), n.cl.size() - 1,
                    chrono::duration<double>(chrono::steady_clock::now() - t0).count());
            routed++;
        }
        int nconf = 0, cells = 0, failed = 0;
        for (auto& n : nets) {
            int c = conflicts(n, true, HFAC);
            if (c) nconf++;
            cells += c;
            if (!n.complete) failed++;
        }
        fprintf(stderr, "iter %d pf %.2f rerouted %d conflicting nets %d (cells %d) failed %d\n", it, PF, routed, nconf, cells, failed);
        if (getenv("HOT") && (it % 5 == 4 || nconf == 0)) {   // conflict hotspots in 1 mm bins
            map<pair<int,int>, set<string>> bins;
            for (auto& n : nets) for (auto& p : n.paths) for (size_t k = 0; k < p.size(); k++) {
                int l = p[k] / N, c = p[k] % N;
                if (fld[l][c] > 1) bins[{(int)((c % NX) * G), (int)((c / NX) * G)}].insert(n.name);
            }
            vector<pair<int, pair<int,int>>> v;
            for (auto& [k2, s2] : bins) v.push_back({(int)s2.size(), k2});
            sort(v.rbegin(), v.rend());
            for (size_t q = 0; q < min<size_t>(v.size(), 25); q++) {
                fprintf(stderr, "  hot (%d,%d):", v[q].second.first, v[q].second.second);
                for (auto& nm : bins[v[q].second]) fprintf(stderr, " %s", nm.c_str());
                fprintf(stderr, "\n");
            }
            for (auto& n : nets) if (!n.complete) fprintf(stderr, "  failed %s %zu/%zu\n", n.name.c_str(), n.paths.size(), n.cl.size() - 1);
        }
        if (nconf + failed < best) {
            best = nconf + failed; bestp.clear(); bestc.clear();
            for (auto& n : nets) { bestp.push_back(n.paths); bestc.push_back(n.complete); }
        }
        if (nconf == 0) break;
        PF *= PFMUL;
        shuffle(order.begin(), order.end(), rng);
        stable_partition(order.begin(), order.end(), [&](int a) { return nets[a].w > 0.2001; });
    }
    // restore best, then drop nets until conflict-free
    for (auto& n : nets) rip_net(n);
    for (int k = 0; k < nn; k++) { nets[k].paths = bestp[k]; nets[k].complete = bestc[k]; if (nets[k].complete) add_net(nets[k]); }
    vector<char> keep(nn, 1);
    while (true) {
        int worst = -1, wc = 0;
        for (int k = 0; k < nn; k++) if (keep[k] && nets[k].complete) { int c = conflicts(nets[k], false, 0); if (c > wc) { wc = c; worst = k; } }
        if (worst < 0) break;
        keep[worst] = 0; rip_net(nets[worst]);
        fprintf(stderr, "drop %s (%d)\n", nets[worst].name.c_str(), wc);
    }
    // strict reroute of dropped / incomplete nets around the kept copper
    STRICT = true;
    vector<int> redo;
    for (int k : order) if ((!keep[k] || !nets[k].complete) && !(getenv("ONLY") && nets[k].name != getenv("ONLY"))) redo.push_back(k);
    sort(redo.begin(), redo.end(), [&](int a, int b) { return nets[a].span < nets[b].span; });
    for (int k : redo) {
        Net& n = nets[k];
        if (keep[k]) rip_net(n);
        route_net(n); add_net(n); keep[k] = 1;
        fprintf(stderr, "strict %s %s %zu/%zu\n", n.name.c_str(), n.complete ? "ok" : "partial", n.paths.size(), n.cl.size() - 1);
    }
    STRICT = false;
    int ok = 0; for (int k = 0; k < nn; k++) ok += keep[k] && nets[k].complete;
    fprintf(stderr, "final: %d/%d nets complete and conflict-free\n", ok, nn);
    write_out(argv[3], keep);
}
