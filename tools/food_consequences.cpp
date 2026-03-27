// ============================================================
//  cd_food_consequences.asi
//  Crimson Desert — Food Consequences Mod
//  Autor: claramercury
//  Basado en: statusinfo.pabgb + skill.pabgb (desencriptados)
//  
//  Activa el sistema de frescura (Fresh), procesado de comida
//  (Foodprocessing), y consecuencias negativas (Poison,
//  Confusion, Morale) que ya existen en el motor pero están
//  desactivadas en el lanzamiento base.
// ============================================================

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <fstream>
#include <string>

// ─── Logging ────────────────────────────────────────────────
static std::ofstream g_log;
#define LOG(msg) if(g_log.is_open()) g_log << "[FoodMod] " << msg << "\n", g_log.flush()

// ─── Config (leer desde .ini en la misma carpeta) ───────────
struct Config {
    // Frescura
    bool  freshEnabled          = true;
    float freshDecayRateMin     = 0.02f;  // pérdida de frescura por segundo (min)
    float freshDecayRateMax     = 0.05f;  // pérdida cuando temperatura > tempThreshold
    float tempThreshold         = 35.0f;  // temperatura en la que el decay se acelera

    // Umbrales de frescura para aplicar efectos
    float freshThresholdStale   = 0.50f;  // por debajo → comida en mal estado
    float freshThresholdRotten  = 0.20f;  // por debajo → comida podrida

    // Efectos al consumir comida en mal estado
    bool  staleGivesDebuff      = true;
    float stalePoisonChance     = 0.30f;  // 30 % de envenenar
    float staleConfusionChance  = 0.20f;  // 20 % de confundir
    float staleMoralePenalty    = -10.0f; // penalización fija a Morale

    // Efectos al consumir comida podrida
    bool  rottenGivesDebuff     = true;
    float rottenPoisonChance    = 0.80f;
    float rottenComatoseChance  = 0.15f;  // raro pero posible
    float rottenMoralePenalty   = -25.0f;

    // Jefes — límite de consumibles en combate
    bool  bossConsumableLimit   = true;
    int   maxHealItemsPerBoss   = 3;      // máximo de curaciones durante un jefe
};
static Config g_cfg;

// ─── Offsets del motor (TODO: verificar con cada patch) ─────
// Estos son PLACEHOLDERS — hay que encontrarlos con Cheat Engine
// o pattern scanning una vez tengamos acceso al proceso.
namespace Offsets {
    // Dirección base del objeto PlayerStatus en memoria
    constexpr uintptr_t PLAYER_STATUS_BASE      = 0x0; // PENDIENTE
    // Offsets dentro del struct PlayerStatus
    constexpr uintptr_t OFF_FRESH               = 0x0; // PENDIENTE — stat Fresh
    constexpr uintptr_t OFF_FOODPROCESSING      = 0x0; // PENDIENTE — stat Foodprocessing
    constexpr uintptr_t OFF_MORALE              = 0x0; // PENDIENTE — stat Morale
    constexpr uintptr_t OFF_TEMPERATURE         = 0x0; // PENDIENTE — stat Temperature
    // Funciones del motor para aplicar status effects
    constexpr uintptr_t FN_APPLY_STATUS_EFFECT  = 0x0; // PENDIENTE
    constexpr uintptr_t FN_CONSUME_FOOD_HOOK    = 0x0; // PENDIENTE — gancho en OnConsumeFood
}

// ─── IDs de status effects (del skill.pabgb desencriptado) ──
// Nombres encontrados: Active_Poison, Active_TempUp,
// BuffedAction_Active_Coma, _Panic, _Injured, Confusion
enum class StatusEffect : uint32_t {
    Poison    = 0x0, // PENDIENTE — buscar en skill.pabgb
    Confusion = 0x0,
    Coma      = 0x0,
    Panic     = 0x0,
};

// ─── Utilidades ─────────────────────────────────────────────
static float RandomFloat() {
    return static_cast<float>(rand()) / static_cast<float>(RAND_MAX);
}

// Lee un float de la memoria del proceso (helper seguro)
static float ReadFloat(uintptr_t addr) {
    __try {
        return *reinterpret_cast<float*>(addr);
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        return 0.0f;
    }
}

static void WriteFloat(uintptr_t addr, float val) {
    __try {
        DWORD old;
        VirtualProtect(reinterpret_cast<void*>(addr), sizeof(float),
                       PAGE_EXECUTE_READWRITE, &old);
        *reinterpret_cast<float*>(addr) = val;
        VirtualProtect(reinterpret_cast<void*>(addr), sizeof(float), old, &old);
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        LOG("WriteFloat failed at " << std::hex << addr);
    }
}

// ─── Lógica principal ────────────────────────────────────────

// Llamada cada vez que el jugador consume un alimento.
// addr_food_item: puntero al objeto de item consumido (struct a definir).
static void OnFoodConsumed(uintptr_t addr_food_item) {
    if (!g_cfg.freshEnabled) return;

    // TODO: leer el valor actual de Fresh del item
    float freshValue = ReadFloat(addr_food_item + Offsets::OFF_FRESH);
    LOG("Food consumed, Fresh=" << freshValue);

    bool isStale  = freshValue < g_cfg.freshThresholdStale
                 && freshValue >= g_cfg.freshThresholdRotten;
    bool isRotten = freshValue < g_cfg.freshThresholdRotten;

    if (isRotten && g_cfg.rottenGivesDebuff) {
        LOG("Rotten food — applying effects");
        if (RandomFloat() < g_cfg.rottenPoisonChance)
            LOG("  → Poison applied");   // TODO: llamar FN_APPLY_STATUS_EFFECT(Poison)
        if (RandomFloat() < g_cfg.rottenComatoseChance)
            LOG("  → Coma applied");     // TODO: llamar FN_APPLY_STATUS_EFFECT(Coma)
        // TODO: Morale -= rottenMoralePenalty
    }
    else if (isStale && g_cfg.staleGivesDebuff) {
        LOG("Stale food — applying effects");
        if (RandomFloat() < g_cfg.stalePoisonChance)
            LOG("  → Poison applied");
        if (RandomFloat() < g_cfg.staleConfusionChance)
            LOG("  → Confusion applied");
        // TODO: Morale -= staleMoralePenalty
    }
    else {
        LOG("Fresh food — no negative effects");
    }
}

// Decay de frescura de los items en el inventario (tick periódico)
static void TickFreshDecay(float deltaTime) {
    if (!g_cfg.freshEnabled) return;
    // TODO: iterar sobre el inventario del jugador y aplicar decay
    // rate se modifica si Temperature > tempThreshold
    float temp = ReadFloat(Offsets::PLAYER_STATUS_BASE + Offsets::OFF_TEMPERATURE);
    float rate = (temp > g_cfg.tempThreshold)
                 ? g_cfg.freshDecayRateMax
                 : g_cfg.freshDecayRateMin;
    (void)rate; // quitar cuando la iteración de inventario esté lista
    LOG("FreshDecay tick: temp=" << temp << " rate=" << rate);
}

// ─── Thread principal del mod ────────────────────────────────
static DWORD WINAPI ModThread(LPVOID) {
    // Abrir log
    char path[MAX_PATH];
    GetModuleFileNameA(nullptr, path, MAX_PATH);
    std::string logPath = std::string(path);
    logPath = logPath.substr(0, logPath.rfind('\\')) + "\\cd_food_consequences.log";
    g_log.open(logPath);
    LOG("Mod loaded — Food Consequences v0.1");

    // TODO: leer config desde cd_food_consequences.ini

    // TODO: instalar hook en FN_CONSUME_FOOD_HOOK con MinHook o detours

    // Bucle de tick para decay de frescura
    DWORD lastTick = GetTickCount();
    while (true) {
        DWORD now  = GetTickCount();
        float dt   = (now - lastTick) / 1000.0f;
        lastTick   = now;
        TickFreshDecay(dt);
        Sleep(1000); // tick cada segundo
    }
    return 0;
}

// ─── Punto de entrada DLL ────────────────────────────────────
BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        CreateThread(nullptr, 0, ModThread, nullptr, 0, nullptr);
    }
    return TRUE;
}
