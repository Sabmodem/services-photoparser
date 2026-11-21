{
  description = "ML-среда внутри FHS-окружения с автонастройкой VS Code";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";

      pkgs = import nixpkgs {
        inherit system;
        config = { allowUnfree = true; };
      };
      lib = pkgs.lib;

      # Database tools for migrations
      db-tools = with pkgs; [
        alembic
      ];

      # FHS libraries needed at runtime
      fhs-lib = with pkgs; [
        pkgs.stdenv.cc.cc.lib
        pkgs.zlib
        pkgs.glib
        pkgs.sqlite
      ];

      # 1. Настройка VS Code
      my-vscode = pkgs.vscode-with-extensions.override {
        vscodeExtensions = with pkgs.vscode-extensions; [
          ms-azuretools.vscode-containers
          jnoortheen.nix-ide
          ms-python.python
          ms-python.black-formatter
          ms-python.vscode-pylance
          anthropic.claude-code
        ];
      };

      # FHS wrapper (for running compiled packages, kept for compatibility)
      fhsEntrypoint = pkgs.writeShellScript "ml-fhs-entry" ''
        if [ -f "$PWD/.venv/bin/activate" ]; then
          source "$PWD/.venv/bin/activate"
        fi
        exec bash "$@"
      '';

      fhsEnv = pkgs.buildFHSEnv {
        name = "ml-fhs-env";
        targetPkgs = pkgs: [
          pkgs.uv
          pkgs.opencode
        ] ++ fhs-lib;
        runScript = "${fhsEntrypoint}";
      };

      # LD_LIBRARY_PATH from FHS libraries (for running compiled Python packages)
      fhsLibPaths = lib.makeLibraryPath fhs-lib;
    in
    {
      # devShell для работы `nix develop` и `nix develop -c <cmd>`
      devShells.${system} = {
        # Default shell
        default = pkgs.mkShell {
          packages = [ pkgs.uv fhsEnv ];

          shellHook = ''
            # FHS libraries for compiled packages (PyTorch, etc.)
            export LD_LIBRARY_PATH=${fhsLibPaths}:${pkgs.glibc}/lib:$LD_LIBRARY_PATH

            if [ ! -d .venv ]; then
              echo "ℹ️  Окружение .venv не найдено. Создайте его:"
              echo "    uv venv && uv sync"
            fi

            if [ -f "$PWD/.venv/bin/activate" ]; then
              source "$PWD/.venv/bin/activate"
            fi

            echo "✅ FHS-окружение готово"
            echo "📦 Доступные команды:"
            echo "   uv sync          # Установить зависимости"
            echo "   uv lock          # Сгенерировать lockfile"
            echo "   uv run uvicorn ...  # Запустить API"
            echo "   alembic <cmd>    # Migrations"
            echo ""
          '';
        };

        # Shell для миграций базы данных
        migrations = pkgs.mkShell {
          packages = db-tools ++ [ pkgs.uv fhsEnv ];

          shellHook = ''
            export LD_LIBRARY_PATH=${fhsLibPaths}:${pkgs.glibc}/lib:$LD_LIBRARY_PATH

            if [ -f "$PWD/.venv/bin/activate" ]; then
              source "$PWD/.venv/bin/activate"
            fi

            echo "📦 Database migrations environment"
            echo ""
            echo "Usage:"
            echo "  uv sync          # Install dependencies"
            echo "  alembic upgrade head      # Apply migrations"
            echo "  alembic downgrade 1       # Revert last migration"
            echo "  alembic current           # Check current version"
            echo "  alembic history           # View migration history"
            echo "  alembic revision -m \"msg\" # Generate migration"
            echo ""
            echo "Set DATABASE_URL environment variable for autogenerate:"
            echo "  export DATABASE_URL=postgresql+pg8000://user:pass@host:port/db"
            echo "  alembic revision --autogenerate -m \"msg\""
          '';
        };
      };
    };
}
