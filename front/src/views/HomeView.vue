<script setup lang="ts">
import MainTitle from "@/components/MainTitle.vue"
import JobItem from "@/components/JobItem.vue"
import JobModal from "@/components/JobModal.vue"
</script>
<script lang="ts">
import mmaData from "../../data.json"
import timeData from "../../time.json"
import * as Hangul from "hangul-js"
import { Job, Addr } from "@/models/Job"
import { getCookie, max } from "@/utils/utils"

const primeNumberCountForEachLoadMore = 11;

export default {
    name: "HomeView",
    components: {
        MainTitle,
    },
    data() {
        const entries = [
            "업종",
            "요원형태",
            "고용형태",
            "교대근무",
            "특근잔업",
            "전직자채용가능",
            "현역배정인원",
        ]
        const _data = {
            jobAll: mmaData
                .filter((job) => job.업체명) // 업체명이 없으면 마감된 공고다.
                .map((job) => {
                    return new Job(new Map(Object.entries(job)))
                }),
            kept: new Array<Job>(),
            maxKept: primeNumberCountForEachLoadMore,
            queried: new Map(
                entries.map((entry) => [entry, new Set<string>()])
            ),
            lastUpdate: new Date(timeData.time * 1000),
            regionPool: new Map<string, Set<string>>(), // 시/도: {시군구}
            optionPool: new Map<string, Set<string>>(),
            jobDetailShown: new Job(new Map<string, string>()),
        }
        mmaData.forEach((job) => {
            entries.forEach((entry: string) => {
                const value = job[entry as keyof typeof job]
                if (!_data.optionPool.get(entry))
                    _data.optionPool.set(entry, new Set<string>())
                _data.optionPool.get(entry)!.add(value)
            })
        })
        mmaData.forEach((job) => {
            const region = job.주소.split(" ", 2)
            if (!_data.regionPool.get(region[0]))
                _data.regionPool.set(region[0], new Set<string>())
            _data.regionPool.get(region[0])!.add(region[1])
        })
        _data.queried.set("시/도", new Set<string>())
        _data.queried.set("시군구", new Set<string>())
        _data.queried.set("즐겨찾기", new Set<string>())
        return _data
    },
    mounted() {
        const filterPanel = document.getElementById("filter-panel")!
        const observer = new IntersectionObserver(
            ([e]) => e.target.classList.toggle("sticky", e.intersectionRatio < 1),
            { threshold: [1] }
        )
        observer.observe(filterPanel)
        const params = new URLSearchParams(window.location.search)
        for (const [key, valueArr] of params.entries()) {
            if (this.queried.has(key)) { // A filter has that key.
                for (const value of valueArr.split(",")) {
                    this.toggleOption(key, value, true)
                }
                this.searchByFilter(key)
            } else if (key === "검색어") {
                this.searchByKeyword(valueArr)
            }
        }
        this.searchByRegion()
        this.loadMore(primeNumberCountForEachLoadMore)
        document.addEventListener("scroll", this.onScroll)
    },
    methods: {
        searchByFavorite() {
            const favoriteQueried = this.queried.get("즐겨찾기")!
            const isFavorite = favoriteQueried.has("즐겨찾는 공고")
            const isNotFavorite = favoriteQueried.has("즐겨찾지 않는 공고")
            const favorite = getCookie('favorite')?.split(',') || []
            const favoriteSet = new Set<string>(favorite)
            this.jobAll.forEach((job) => {
                if (favoriteQueried.size === 0)
                    job.filteredOutBy.delete("즐겨찾기")
                else if (isFavorite && favoriteSet.has(job.data.get("공고번호")!))
                    job.filteredOutBy.delete("즐겨찾기")
                else if (isNotFavorite && !favoriteSet.has(job.data.get("공고번호")!))
                    job.filteredOutBy.delete("즐겨찾기")
                else
                    job.filteredOutBy.add("즐겨찾기")
            })
            this.updateParams("즐겨찾기", Array.from(favoriteQueried))
            this.updateKept()
        },
        searchByFilter(key: string) {
            this.jobAll.forEach((job) => {
                const queried_value = this.queried.get(key)!
                const job_value = job.data.get(key)!
                if (queried_value.size === 0 || queried_value.has(job_value))
                    job.filteredOutBy.delete(key)
                else job.filteredOutBy.add(key)
            })
        },
        searchByKeyword(name: string) {
            const searcher = new Hangul.Searcher(name)
            const entryToSearch = ["업체명", "담당업무", "비고"];
            this.jobAll.forEach((job) => {
                job.filteredOutBy.add("검색어")
                for (const entry of entryToSearch) {
                    const value = job.data.get(entry)!
                    if (searcher.search(value) !== -1) {
                        job.filteredOutBy.delete("검색어")
                        break
                    }
                }
            })
        },
        searchByRegion() {
            const sidoQueried = this.queried.get("시/도")!
            const sigunguQueried = this.queried.get("시군구")!
            this.jobAll.forEach((job) => {
                const region = job.data.get("주소")!.split(" ", 2)
                job.filteredOutBy.delete("시/도")
                if (sidoQueried.size === 0 || sidoQueried.has(region[0]))
                    job.filteredOutBy.delete("시/도")
                else job.filteredOutBy.add("시/도")
                job.filteredOutBy.delete("시군구")
                if (sigunguQueried.size === 0 || sigunguQueried.has(region[1]))
                    job.filteredOutBy.delete("시군구")
                else job.filteredOutBy.add("시군구")
            })
        },
        toggleOption(entry: string, value: string, checked: boolean) {
            const queried_values = this.queried.get(entry)!
            if (checked) queried_values.add(value)
            else queried_values.delete(value)
            if (entry === "시/도") {
                if (!checked) {
                    const sigunguSelected = this.queried.get("시군구")!
                    this.regionPool.get(value)!.forEach((sigungu) => {
                        sigunguSelected.delete(sigungu) // BUG: 이름이 같은 시군구가 존재할 가능성.
                    })
                    this.updateParams("시군구", Array.from(sigunguSelected!))
                }
                this.searchByRegion()
            } else if (entry === "즐겨찾기") {
                this.searchByFavorite()
            } else {
                this.searchByFilter(entry)
            }
            this.updateParams(entry, Array.from(this.queried.get(entry)!))
        },
        updateParams(key: string, values: string[]) {
            if (values.length === 0) this.params.delete(key)
            else this.params.set(key, values.join(","))
            window.history.replaceState(
                {},
                "",
                `${window.location.pathname}?${this.params.toString()}`
            )
        },
        loadMore(count: number) {
            this.kept.push(...this.matches.slice(this.kept.length, this.kept.length + count))
        },
        // infinite scroll.
        onScroll() {
            const scrollHeight = document.documentElement.scrollHeight;
            const scrollTop = document.documentElement.scrollTop;
            const clientHeight = document.documentElement.clientHeight;
            const lastElement = document.querySelector("#list > div:last-child");
            if (scrollTop + clientHeight >= scrollHeight - lastElement!.clientHeight / 2) {
                this.loadMore(primeNumberCountForEachLoadMore)
                this.updateKept()
            }
        },
        updateKept() {
            this.kept = this.matches.slice(0, max(this.kept.length, this.maxKept))
            this.maxKept = max(this.kept.length, this.maxKept);
        },
        setShownJob(job: Job) {
            this.jobDetailShown = job
        }
    },
    computed: {
        params() {
            return new URLSearchParams(window.location.search)
        },
        sigunguPool() {
            const pool = Array<Addr>()
            const sidoQueried = this.queried.get("시/도")!
            if (sidoQueried.size === 0) return pool
            this.regionPool.forEach((value, key) => {
                if (sidoQueried!.has(key)) {
                    value.forEach((sigungu) => {
                        pool.push(new Addr(key, sigungu))
                    })
                }
            })
            return pool
        },
        matches() {
            return this.jobAll.filter((job) => job.filteredOutBy.size === 0)
        }
    }
}
</script>
<template>
    <JobModal :job="jobDetailShown"></JobModal>
    <MainTitle></MainTitle>
    <div>현재 공고가 총 {{ mmaData.length }}개 있습니다.</div>
    <div id="filter-panel" class="p-1">
        <div class="dropdown" v-for="entry in optionPool.keys()" :key="entry">
            <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false" type="button">{{
                entry }}</button>
            <ul class="dropdown-menu">
                <li v-for="option in optionPool.get(entry)" :key="String(option)" class="p-1">
                    <label :for="option" class="px-1">{{ option }}</label>
                    <input :name="option" type="checkbox" :checked="queried.get(entry)!.has(option)"
                        @change="toggleOption(entry, option, ($event.target! as HTMLInputElement).checked); updateKept()">
                </li>
            </ul>
        </div>
        <div class="dropdown">
            <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false"
                type="button">시/도</button>
            <ul class="dropdown-menu">
                <li v-for="sido in Array.from(regionPool.keys()).sort()" :key="String(sido)" class="p-1">
                    <label :for="sido" class="px-1">{{ sido }}</label>
                    <input :name="sido" type="checkbox" :checked="queried.get('시/도')!.has(sido)"
                        @change="toggleOption('시/도', sido, ($event.target! as HTMLInputElement).checked); updateKept()">
                </li>
            </ul>
        </div>
        <div class="dropdown">
            <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false"
                type="button">시군구</button>
            <ul class="dropdown-menu">
                <li v-for="addr in sigunguPool" :key="String(addr)" class="p-1">
                    <label :for="addr.시도 + addr.시군구" class="px-1">{{ addr.시도 }} {{ addr.시군구 }}</label>
                    <input :name="addr.시도 + addr.시군구" type="checkbox" :checked="queried.get('시군구')!.has(addr.시군구)"
                        @change="toggleOption('시군구', addr.시군구, ($event.target! as HTMLInputElement).checked); searchByRegion(); updateKept();">
                </li>
            </ul>
        </div>
        <div class="dropdown">
            <button class="btn btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false"
                type="button">즐겨찾기</button>
            <ul class="dropdown-menu">
                <li v-for="option in ['즐겨찾는 공고', '즐겨찾지 않는 공고']" :key="option" class="p-1">
                    <label :for="option" class="px-1">{{ option }}</label>
                    <input :name="option" type="checkbox" :checked="queried.get('즐겨찾기')!.has(option)"
                        @change="toggleOption('즐겨찾기', option, ($event.target! as HTMLInputElement).checked); searchByFavorite(); updateKept();">
                </li>
            </ul>
        </div>
        <input type="text" class="form-control w-50 my-1" placeholder="삼성전자, 운전가능자, Unity, ..."
            @input="searchByKeyword(($event.target! as HTMLInputElement).value); updateParams('검색어', [($event.target! as HTMLInputElement).value]); updateKept();">
    </div>
    <div id="list" class="grid gap-3 m-3">
        <template v-for="job in kept" :key="job">
            <JobItem :job="job" @showDetail="setShownJob(job)">
            </JobItem>
        </template>
    </div>
    <div id="last-update">
        최근 갱신: {{ lastUpdate.toLocaleDateString("ko-KR", {
            year: "numeric",
            month: "short",
            day: "numeric",
            weekday: "long",
            hour: "numeric",
            minute: "numeric",
            second: "numeric"
        }) }}
    </div>
    <div id="github-icon" class="p-1">
        <a href="https://github.com/TrulyBright/mma-work-crawler" id="github-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-github"
                viewBox="0 0 16 16">
                <path
                    d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
            </svg>
        </a>
    </div>
</template>
<style>
#filter-panel {
    position: sticky;
    top: -1px;
    z-index: 999;
    background: white;
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    padding: 0.5rem;
}

#filter-panel.sticky {
    box-shadow: 0 0 0.5rem rgba(0, 0, 0, 0.1);
}

.dropdown-menu {
    max-height: 20rem;
    overflow-y: auto;
    min-width: max-content;
}

#list {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
}

@media (min-width: 280px) {
    #list {
        grid-template-columns: 1fr;
    }
}

@media (min-width: 480px) {
    #list {
        grid-template-columns: 1fr 1fr;
    }
}

@media (min-width: 768px) {
    #list {
        grid-template-columns: 1fr 1fr 1fr;
    }
}

@media (min-width: 1024px) {
    #list {
        grid-template-columns: 1fr 1fr 1fr 1fr;
    }
}

#github-icon {
    display: flex;
    justify-content: center;
    align-items: center;
    color: black;
}

#fields-button {
    display: flex;
    flex-direction: row;
    justify-content: left;
}

#favorite-form {
    display: flex;
    flex-direction: row;
    align-items: center;
}
</style>
