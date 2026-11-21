{
  description = "ML-среда внутри FHS-окружения с автонастройкой VS Code";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";

      pkgs = import nixpkgs {
        inherit system;
        config = { allowUnfree = true; };
      };

      # Database tools for migrations
      db-tools = with pkgs; [
        alembic
        sqlalchemy
        psycopg2
        pg8000
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

      # Точка входа FHS: активируем .venv (если есть) и отдаём интерактивный bash
      fhsEntrypoint = pkgs.writeShellScript "ml-fhs-entry" ''
        if [ -f "$PWD/.venv/bin/activate" ]; then
          source "$PWD/.venv/bin/activate"
        fi
        exec bash "$@"
      '';

      # 2. Создание изолированного FHS-окружения
      fhsEnv = pkgs.buildFHSEnv {
        name = "ml-fhs-env";
        targetPkgs = pkgs: [
          my-vscode
          pkgs.uv

          # Системные библиотеки, нужные для ML-пакетов (PyTorch, Cuda-драйверы и т.д.)
          pkgs.stdenv.cc.cc.lib
          pkgs.zlib
          pkgs.glib
          pkgs.sqlite
          pkgs.opencode
          # pkgs.pyright   # раскомментируйте, если нужен pyright как CLI
          # pkgs.openssl   # добавьте, если uv/pip будут ругаться на TLS
        ];
        runScript = "${fhsEntrypoint}";
      };
    in
    {
      # 3. Обертка в devShell для работы команды `nix develop`
      devShells.${system}.default = pkgs.mkShell {
        packages = [ fhsEnv ];

        shellHook = ''
          if [ ! -d .venv ]; then
            echo "ℹ️  Окружение .venv не найдено. Создайте его внутри FHS:"
            echo "    uv venv --python 3.12 && uv sync"
          fi
          echo "✅ Входим в FHS-окружение..."
          echo "📦 Доступные команды:"
          echo "   nix develop -c alembic <command>    # Alembic migrations"
          echo "   nix develop -c alembic --help       # Alembic help"
          echo "   nix develop -c python run.sh        # Run API server"
          echo ""
          exec ${fhsEnv}/bin/ml-fhs-env
        '';
      };

      # 4. Shell для миграций базы данных
      devShells.${system}.migrations = pkgs.mkShell {
        packages = db-tools ++ [
          fhsEnv
        ];

        shellHook = ''
          echo "📦 Database migrations environment"
          echo ""
          echo "Usage:"
          echo "  alembic upgrade head      # Apply migrations"
          echo "  alembic downgrade 1       # Revert last migration"
          echo "  alembic current           # Check current version"
          echo "  alembic history           # View migration history"
          echo "  alembic revision -m "msg" # Generate migration"
          echo ""
          echo "Set DATABASE_URL environment variable for autogenerate:"
          echo "  export DATABASE_URL=postgresql+pg8000://user:pass@host:port/db"
          echo "  alembic revision --autogenerate -m "msg""
        '';
      };
    };
}
