{
  description = "Indigo cheminformatics toolkit: native library, Python bindings, and HTTP service";

  # Use a release branch: cache.nixos.org only has prebuilt paths for revisions
  # Hydra built, so an arbitrary rev turns cache hits into local rebuilds.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  # third_party/lunasvg pulls plutovg in with FetchContent at configure time,
  # which cannot reach the network from inside the Nix build sandbox. Lock it
  # here instead and hand it to CMake via FETCHCONTENT_SOURCE_DIR_PLUTOVG.
  inputs.plutovg = {
    url = "github:sammycage/plutovg/v1.1.0";
    flake = false;
  };

  # The service pins dependency versions that current nixpkgs does not carry
  # (and lacks flasgger entirely), so build them from PyPI via uv2nix instead.
  inputs.pyproject-nix = {
    url = "github:pyproject-nix/pyproject.nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.uv2nix = {
    url = "github:pyproject-nix/uv2nix";
    inputs.pyproject-nix.follows = "pyproject-nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.pyproject-build-systems = {
    url = "github:pyproject-nix/build-system-pkgs";
    inputs.pyproject-nix.follows = "pyproject-nix";
    inputs.uv2nix.follows = "uv2nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    { self, ... }@inputs:

    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem =
        f:
        inputs.nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            inherit system;
            pkgs = import inputs.nixpkgs { inherit system; };
          }
        );
    in
    {
      packages = forEachSupportedSystem (
        { pkgs, system }:
        let
          lib = pkgs.lib;
          # Non-primary interpreters have much thinner binary-cache coverage.
          python = pkgs.python3;

          # Version comes from api/indigo-version.cmake's INDIGO_DEFAULT_VERSION.
          # The build has no git metadata in the sandbox, so cmake falls back to it.
          indigoVersion =
            let
              m = builtins.match ''.*set\(INDIGO_DEFAULT_VERSION "([^"]+)"\).*''
                (builtins.readFile ./api/indigo-version.cmake);
            in
            if m == null then "0.0.0" else builtins.head m;

          # Allowlist only what CMake reads, so unrelated edits (flake.nix, docs)
          # do not rehash the source and force a rebuild of the native library.
          src = lib.fileset.toSource {
            root = ./.;
            fileset = lib.fileset.unions [
              ./CMakeLists.txt
              ./cmake
              ./third_party
              ./core
              ./api
              ./bingo
              ./utils
            ];
          };

          # `Lib._library_path` in api/python/indigo/_common/lib.py looks for
          # lib/<system>-<machine>/libindigo.<ext>, so mirror that naming here.
          systemName = if pkgs.stdenv.hostPlatform.isDarwin then "darwin" else "linux";
          machineName =
            if pkgs.stdenv.hostPlatform.isAarch64 then "aarch64" else "x86_64";
          libSubdir = "${systemName}-${machineName}";
          libExt = if pkgs.stdenv.hostPlatform.isDarwin then "dylib" else "so";

          # setup.py accepts only this fixed set of --plat-name values and keys
          # the packaged lib/ glob off them.
          platName =
            {
              "aarch64-darwin" = "macosx_11_0_arm64";
              "x86_64-darwin" = "macosx_10_7_intel";
              "aarch64-linux" = "manylinux2014_aarch64";
              "x86_64-linux" = "manylinux1_x86_64";
            }
            .${system};

          indigo-native = pkgs.stdenv.mkDerivation {
            pname = "indigo-native";
            version = indigoVersion;
            inherit src;

            nativeBuildInputs = [
              pkgs.cmake
              pkgs.pkg-config
            ];

            # third_party/CMakeLists.txt builds the vendored freetype only under
            # Emscripten; elsewhere third_party/cairo links system freetype and
            # fontconfig (and hardcodes /usr/include/freetype2, which does not
            # exist here -- the compiler wrapper supplies the real include path).
            buildInputs = lib.optionals pkgs.stdenv.hostPlatform.isLinux [
              pkgs.freetype
              pkgs.fontconfig
            ];

            # third_party/ is vendored, so BUILD_STANDALONE=ON avoids system
            # library lookups.
            cmakeFlags = [
              "-DFETCHCONTENT_FULLY_DISCONNECTED=ON"
              "-DFETCHCONTENT_SOURCE_DIR_PLUTOVG=${inputs.plutovg}"
              "-DBUILD_INDIGO=ON"
              "-DBUILD_INDIGO_UTILS=ON"
              "-DBUILD_INDIGO_WRAPPERS=OFF"
              "-DBUILD_BINGO=OFF"
              "-DBUILD_BINGO_ELASTIC=OFF"
              "-DBUILD_STANDALONE=ON"
              "-DENABLE_TESTS=OFF"
              "-DCMAKE_BUILD_TYPE=Release"
            ];

            # utils/indigo-depict/main.c relies on implicit int, which modern
            # clang rejects. setup.sh passes the same flag.
            env.NIX_CFLAGS_COMPILE = "-Wno-implicit-int";

            # CMake writes the built artifacts to <source>/dist rather than to the
            # build tree (see DIST_DIRECTORY in cmake/setup.cmake), so install from
            # there instead of running `cmake --install`.
            installPhase = ''
              runHook preInstall

              mkdir -p "$out/lib/${libSubdir}" "$out/bin"
              cp ../dist/lib/${libSubdir}/*.${libExt} "$out/lib/${libSubdir}/"

              # utils/*/CMakeLists.txt copy their executables to dist/utils.
              for util in ../dist/utils/*; do
                if [ -f "$util" ]; then
                  install -Dm755 "$util" "$out/bin/$(basename "$util")"
                fi
              done

              runHook postInstall
            '';

            # libindigo-renderer/-inchi/libbingo-nosql link the shared indigo
            # target, so CMake bakes a build-tree RPATH into them. Nothing
            # rewrites it, because installPhase copies out of dist/ rather than
            # running `cmake --install`, and fixupPhase rejects /build/ refs.
            # They are siblings in one directory, so $ORIGIN resolves libindigo.
            # Must be preFixup: fixupPhase's own /build/ reference check would
            # fail on the stale RPATH before a postFixup hook ever ran.
            #
            # Prepend rather than replace: libindigo-renderer also needs freetype
            # and fontconfig from the store, and dropping those entries makes it
            # silently resolve against the host's /usr/lib instead. Filter the
            # build-tree entries out and keep the rest.
            preFixup = lib.optionalString pkgs.stdenv.hostPlatform.isLinux ''
              for so in "$out"/lib/${libSubdir}/*.${libExt}; do
                keep=$(patchelf --print-rpath "$so" | tr ':' '\n' \
                  | grep -v '^/build' | grep -v '^$' | paste -sd: -)
                patchelf --set-rpath "\$ORIGIN''${keep:+:$keep}" "$so"
              done
            '';

            meta = {
              description = "Indigo cheminformatics native libraries";
              license = lib.licenses.asl20;
              platforms = supportedSystems;
            };
          };

          # Built directly rather than via the upstream `indigo-python` CMake
          # target, which builds a wheel per platform tag and requires an active
          # virtualenv.
          mkEpamIndigo = python: python.pkgs.buildPythonPackage {
            pname = "epam-indigo";
            version = indigoVersion;
            format = "setuptools";

            src = "${src}/api/python";

            nativeBuildInputs = [ python.pkgs.wheel ];
            propagatedBuildInputs = [ indigo-native ];

            # setup.py requires a --plat-name it recognises, and maps that tag to
            # the lib/ glob it packages.
            setupPyBuildFlags = [ "--plat-name=${platName}" ];

            preBuild = ''
              mkdir -p indigo/lib/${libSubdir}
              cp ${indigo-native}/lib/${libSubdir}/*.${libExt} indigo/lib/${libSubdir}/
            '';

            # Copy the native libs in directly; setup.py's own packaging of them
            # is keyed to --plat-name and does not survive the wheel install.
            postInstall = ''
              site="$out/${python.sitePackages}/indigo"
              mkdir -p "$site/lib/${libSubdir}"
              cp indigo/lib/${libSubdir}/*.${libExt} "$site/lib/${libSubdir}/"
            '';

            # Tests need reference renderings not shipped in the python subtree.
            doCheck = false;

            pythonImportsCheck = [
              "indigo"
              "indigo.indigo"
              "indigo.inchi"
              "indigo.renderer"
            ];

            meta = {
              description = "Python bindings for the Indigo toolkit";
              license = lib.licenses.asl20;
            };
          };

          epam-indigo = mkEpamIndigo python;

          # Dependencies come from nix/service/uv.lock, which mirrors
          # utils/indigo-service/backend/service/requirements.txt. Keep the two in
          # sync. 3.11 is the closest available to the Python 3.10 that the
          # Ubuntu 22.04 image in backend/Dockerfile runs.
          servicePython = pkgs.python311;

          uvWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
            workspaceRoot = ./nix/service;
          };

          # Prefer wheels: these pins predate current build backends, so several
          # of their sdists no longer configure against modern setuptools.
          uvOverlay = uvWorkspace.mkPyprojectOverlay {
            sourcePreference = "wheel";
          };

          servicePythonSet =
            (pkgs.callPackage inputs.pyproject-nix.build.packages {
              python = servicePython;
            }).overrideScope
              (
                lib.composeManyExtensions [
                  inputs.pyproject-build-systems.overlays.default
                  uvOverlay
                  # Built from this repo rather than fetched from PyPI, so uv2nix
                  # knows nothing about it. Must use pyproject-nix's builder, not
                  # nixpkgs' buildPythonPackage: mkVirtualEnv's resolver requires
                  # metadata that only the former attaches.
                  (final: prev: {
                    epam-indigo = final.stdenv.mkDerivation {
                      pname = "epam-indigo";
                      version = indigoVersion;
                      src = "${src}/api/python";

                      nativeBuildInputs =
                        [ final.pyprojectHook ]
                        ++ final.resolveBuildSystem {
                          setuptools = [ ];
                          wheel = [ ];
                        };

                      # setup.py hard-fails without a --plat-name it recognises,
                      # and uv drives the PEP 517 hook directly, with no way to
                      # forward one. Its other branch globs lib/**/*, which is
                      # exactly the one platform's libs that preBuild stages --
                      # and the wheel is pure Python, so the tag means nothing.
                      postPatch = ''
                        substituteInPlace setup.py \
                          --replace-fail \
                            'if sys.argv[1] == "bdist_wheel":' \
                            'if False:'
                      '';

                      preBuild = ''
                        mkdir -p indigo/lib/${libSubdir}
                        cp ${indigo-native}/lib/${libSubdir}/*.${libExt} \
                          indigo/lib/${libSubdir}/
                      '';
                    };
                  })
                  # The only dependency without a PyPI wheel, and its setup.py
                  # never declared setuptools as a build requirement -- which
                  # uv's build isolation enforces.
                  (final: prev: {
                    flasgger = prev.flasgger.overrideAttrs (old: {
                      nativeBuildInputs =
                        (old.nativeBuildInputs or [ ])
                        ++ final.resolveBuildSystem { setuptools = [ ]; };
                    });
                  })
                ]
              );

          servicePythonEnv = servicePythonSet.mkVirtualEnv "indigo-service-env" (
            uvWorkspace.deps.default // { epam-indigo = [ ]; }
          );

          # app.py does `config.from_pyfile("config.py")` relative to its own
          # directory, and the repo ships no such file; installPhase creates an
          # empty one. Real settings live in v2/common/config.py.
          indigo-service = pkgs.stdenv.mkDerivation {
            pname = "indigo-service";
            version = indigoVersion;
            src = "${src}/utils/indigo-service/backend/service";

            nativeBuildInputs = [ pkgs.makeWrapper ];
            buildInputs = [ servicePythonEnv ];

            dontBuild = true;

            installPhase = ''
              runHook preInstall

              mkdir -p "$out/libexec/indigo-service"
              cp -r ./* "$out/libexec/indigo-service/"
              touch "$out/libexec/indigo-service/config.py"

              makeWrapper ${servicePythonEnv}/bin/python "$out/bin/indigo-service" \
                --add-flags "$out/libexec/indigo-service/app.py" \
                --add-flags "-s" \
                --chdir "$out/libexec/indigo-service"

              # Mirrors start_service.sh. --listen stays overridable.
              makeWrapper ${servicePythonEnv}/bin/waitress-serve "$out/bin/indigo-service-waitress" \
                --add-flags "app:app" \
                --chdir "$out/libexec/indigo-service" \
                --set PYTHONPATH "$out/libexec/indigo-service"

              runHook postInstall
            '';

            meta = {
              description = "Indigo HTTP service (Flask)";
              license = lib.licenses.asl20;
              mainProgram = "indigo-service";
            };
          };
        in
        {
          inherit indigo-native epam-indigo indigo-service;
          inherit servicePythonEnv;
          default = indigo-service;
        }
      );

      apps = forEachSupportedSystem (
        { pkgs, system }:
        {
          default = {
            type = "app";
            program = "${self.packages.${system}.indigo-service}/bin/indigo-service";
          };
          indigo-service = {
            type = "app";
            program = "${self.packages.${system}.indigo-service}/bin/indigo-service";
          };
        }
      );

      devShells = forEachSupportedSystem (
        { pkgs, system }:
        let
          lib = pkgs.lib;
          # Non-primary interpreters have much thinner binary-cache coverage.
          python = pkgs.python3;
        in
        {
          default = pkgs.mkShellNoCC {
            venvDir = ".venv";

            postShellHook = ''
              venvVersionWarn() {
              	local venvVersion
              	venvVersion="$("$venvDir/bin/python" -c 'import platform; print(platform.python_version())')"

              	[[ "$venvVersion" == "${python.version}" ]] && return

              	cat <<EOF
              Warning: Python version mismatch: [$venvVersion (venv)] != [${python.version}]
                       Delete '$venvDir' and reload to rebuild for version ${python.version}
              EOF
              }

              venvVersionWarn
            '';

            packages = with python.pkgs; with pkgs; [
              venvShellHook
              pip

              llvmPackages_21.clang-tools
              llvmPackages_21.libcxxClang
              lldb_21
              cmake
            ];
          };
        }
      );
    };
}
